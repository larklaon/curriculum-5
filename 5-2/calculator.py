# calculator.py
# Python 3.x, PyQt5
# PEP 8 준수, 문자열은 기본적으로 ' ' 사용

from decimal import (
    Decimal,
    getcontext,
    localcontext,
    DivisionByZero,
    InvalidOperation,
    Overflow,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
)
import sys


class Calculator:
    """연산 엔진: 상태와 사칙연산/부호/퍼센트/= 처리"""

    MAX_DIGITS = 12  # 디스플레이 자릿수 제한

    def __init__(self) -> None:
        # Decimal 전역 컨텍스트(필요 시 조정)
        ctx = getcontext()
        ctx.prec = 28  # 충분한 내부 정밀도
        # 안전을 위해 기본 트랩 유지: DivisionByZero, Overflow, InvalidOperation

        self.reset()

    # 필수 API
    def add(self, a: Decimal, b: Decimal) -> Decimal:
        return a + b

    def subtract(self, a: Decimal, b: Decimal) -> Decimal:
        return a - b

    def multiply(self, a: Decimal, b: Decimal) -> Decimal:
        return a * b

    def divide(self, a: Decimal, b: Decimal) -> Decimal:
        # 0 나누기 방지: Decimal 컨텍스트에서 DivisionByZero 트랩
        with localcontext() as ctx:
            # 컨텍스트 그대로 사용하여 예외를 던지게 함
            return a / b

    def reset(self) -> None:
        self._acc = None  # 이전 값(Decimal)
        self._op = None  # 대기 연산자: '+', '-', '*', '/'
        self._cur = '0'  # 현재 입력(문자열)
        self._error = False  # 오류 상태
        self._last_equals = False  # 직전 입력이 '=' 여부

    def negative_positive(self) -> None:
        if self._error:
            return
        if self._cur.startswith('-'):
            self._cur = self._cur[1:]
        else:
            if self._cur != '0':
                self._cur = '-' + self._cur

    def percent(self) -> None:
        if self._error:
            return
        try:
            x = self._to_decimal(self._cur)
            if self._acc is not None and self._op in ('+', '-', '*', '/'):
                # 이항 문맥: prev * (x/100)
                x = (self._acc * x) / Decimal('100')
            else:
                # 단항 문맥: x/100
                x = x / Decimal('100')
            self._cur = self._format_decimal(x)
        except (DivisionByZero, Overflow, InvalidOperation):
            self._set_error()

    def input_digit(self, d: str) -> None:
        if self._error:
            return
        if self._last_equals and self._op is None:
            # = 직후 새 입력이면 새 계산 시작
            self._acc = None
            self._cur = '0'
            self._last_equals = False

        if self._cur == '0':
            self._cur = d
        else:
            if self._too_long_next(self._cur + d):
                return
            self._cur += d

    def input_dot(self) -> None:
        if self._error:
            return
        if '.' in self._cur:
            return
        if self._too_long_next(self._cur + '.'):
            return
        self._cur += '.'

    def set_operator(self, op: str) -> None:
        """op in {'+','−','×','÷'} UI 기호를 내부 기호로 변환"""
        if self._error:
            return
        internal = self._to_internal_op(op)

        try:
            if self._acc is None:
                # 첫 연산자: 현재 입력을 축적
                self._acc = self._to_decimal(self._cur)
                self._op = internal
                self._cur = '0'
                self._last_equals = False
                return

            # acc와 cur로 직전 연산을 수행하고, 새 연산자로 교체
            if self._cur != '0' or self._op in ('*', '/'):
                self._acc = self._apply_op(self._acc, self._to_decimal(self._cur), self._op)
                self._cur = '0'
            self._op = internal
            self._last_equals = False

        except (DivisionByZero, Overflow, InvalidOperation):
            self._set_error()

    def equal(self) -> None:
        if self._error:
            return
        if self._op is None or self._acc is None:
            # 단독 = 인 경우 현재 값 유지
            self._last_equals = True
            return
        try:
            result = self._apply_op(self._acc, self._to_decimal(self._cur), self._op)
            self._acc = None
            self._op = None
            self._cur = self._format_decimal(result)
            self._last_equals = True
        except (DivisionByZero, Overflow, InvalidOperation):
            self._set_error()

    # 표시 문자열
    def display_text(self) -> str:
        return 'Error' if self._error else self._cur

    # 내부 유틸
    def _apply_op(self, a: Decimal, b: Decimal, op: str) -> Decimal:
        if op == '+':
            return self.add(a, b)
        if op == '-':
            return self.subtract(a, b)
        if op == '*':
            return self.multiply(a, b)
        if op == '/':
            return self.divide(a, b)
        return b

    def _to_internal_op(self, ui_op: str) -> str:
        mapping = {'+': '+', '−': '-', '×': '*', '÷': '/'}
        return mapping.get(ui_op, ui_op)

    def _to_decimal(self, s: str) -> Decimal:
        # 문자열에서 Decimal로, 앞자리 0과 '.' 처리
        if s == '.' or s == '-.':
            s = s.replace('.', '0.').replace('-.', '-0.')
        return Decimal(s)

    def _format_decimal(self, x: Decimal) -> str:
        # 정규화 및 길이 제한
        s = format(x.normalize(), 'f')
        if 'E' in str(x):  # 과도한 지수 표기는 단순화
            s = '{:f}'.format(x)
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        if s == '' or s == '-':
            s = '0'
        # 길이 제한: 부호와 소수점 포함
        if len(s.replace('-', '').replace('.', '')) > self.MAX_DIGITS:
            # 자릿수 초과는 지수 표기 대신 오류로 단순 처리
            raise Overflow
        return s

    def _too_long_next(self, s: str) -> bool:
        # 다음 입력이 자릿수 제한을 넘기는지 검사
        digits = s.replace('-', '').replace('.', '')
        return len(digits) > self.MAX_DIGITS

    def _set_error(self) -> None:
        self._error = True
        self._acc = None
        self._op = None
        self._cur = 'Error'


class CalculatorWindow(QWidget):
    """PyQt5 UI: 버튼 → Calculator 엔진 연결"""

    def __init__(self) -> None:
        super().__init__()
        self.engine = Calculator()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle('Calculator')
        root = QVBoxLayout()
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        self.setLayout(root)

        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        font = QFont(self.display.font())
        font.setPointSize(28)
        self.display.setFont(font)
        self.display.setText(self.engine.display_text())
        root.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(6)
        root.addLayout(grid)

        buttons = [
            ['AC', '+/-', '%', '÷'],
            ['7',  '8',   '9', '×'],
            ['4',  '5',   '6', '−'],
            ['1',  '2',   '3', '+'],
            ['0',  '.',   '=', ],
        ]

        for r, row in enumerate(buttons):
            for c, label in enumerate(row):
                btn = QPushButton(label)
                btn.setMinimumHeight(56)
                btn.setCursor(Qt.PointingHandCursor)
                # clicked는 checked(bool) 인자를 내보내므로 첫 인자를 흡수하도록 작성
                btn.clicked.connect(lambda checked=False, ch=label: self.on_button(ch))

                if label == '0':
                    grid.addWidget(btn, r, 0, 1, 2)
                else:
                    if r == 4 and label in ('.', '='):
                        grid.addWidget(btn, r, 2 + (0 if label == '.' else 1))
                    else:
                        grid.addWidget(btn, r, c)

        self.resize(360, 520)

    def on_button(self, ch: str) -> None:
        if ch == 'AC':
            self.engine.reset()
        elif ch == '+/-':
            self.engine.negative_positive()
        elif ch == '%':
            self.engine.percent()
        elif ch == '=':
            self.engine.equal()
        elif ch in {'+', '−', '×', '÷'}:
            self.engine.set_operator(ch)
        elif ch == '.':
            self.engine.input_dot()
        elif ch.isdigit():
            self.engine.input_digit(ch)

        self.display.setText(self.engine.display_text())


def main() -> None:
    app = QApplication(sys.argv)
    w = CalculatorWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
