# engineering_calculator.py
# Python 3.x, PyQt5
# 표준 라이브러리 + PyQt만 사용, PEP 8 준수, 문자열은 기본 ' ' 사용

import sys
import math  # 삼각/쌍곡/상수/각도 변환 [표준 모듈]

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

# 이전 과제의 Calculator를 재사용
# 동일 디렉터리에 calculator.py가 있다고 가정
from calculator import Calculator  # add/subtract/multiply/divide/percent 등 포함


class EngineeringCalculator(Calculator):
    """공학 기능 확장: sin/cos/tan/sinh/cosh/tanh/π/x²/x³ + 각도 단위 전환"""

    def __init__(self) -> None:
        super().__init__()
        self._angle_in_radians = False  # False: Deg(아이폰 기본 가정), True: Rad

    # 각도 단위 제어
    def set_angle_unit(self, use_radians: bool) -> None:
        self._angle_in_radians = use_radians

    # 공용 유틸
    def _get_current_number(self) -> float:
        s = self.display_text()
        if s in ('', 'Error'):
            raise ValueError('invalid state')
        # 연산식 중간이 아닌 숫자만 처리(간단화)
        for ch in '+−×÷()%':
            if ch in s:
                raise ValueError('not a pure number')
        return float(s)

    def _set_from_float(self, val: float) -> None:
        # 간단한 표시 포맷: 불필요한 0/소수점 제거 + 길이 제한
        s = ('{:.12g}'.format(val)).rstrip('0').rstrip('.') if not math.isnan(val) else 'Error'
        if s == '' or s == '-':
            s = '0'
        # 길이 제한
        if len(s.replace('-', '').replace('.', '')) > 12:
            self._set_error()
            return
        self._cur = s

    def _to_radians_if_needed(self, x: float) -> float:
        return x if self._angle_in_radians else math.radians(x)

    # 요구 기능 구현
    def sin(self) -> None:
        try:
            x = self._get_current_number()
            y = math.sin(self._to_radians_if_needed(x))
            self._set_from_float(y)
        except (ValueError, OverflowError):
            self._set_error()

    def cos(self) -> None:
        try:
            x = self._get_current_number()
            y = math.cos(self._to_radians_if_needed(x))
            self._set_from_float(y)
        except (ValueError, OverflowError):
            self._set_error()

    def tan(self) -> None:
        try:
            x = self._get_current_number()
            rad = self._to_radians_if_needed(x)
            y = math.tan(rad)
            self._set_from_float(y)
        except (ValueError, OverflowError):
            self._set_error()

    def sinh(self) -> None:
        try:
            x = self._get_current_number()
            y = math.sinh(x)
            self._set_from_float(y)
        except (ValueError, OverflowError):
            self._set_error()

    def cosh(self) -> None:
        try:
            x = self._get_current_number()
            y = math.cosh(x)
            self._set_from_float(y)
        except (ValueError, OverflowError):
            self._set_error()

    def tanh(self) -> None:
        try:
            x = self._get_current_number()
            y = math.tanh(x)
            self._set_from_float(y)
        except (ValueError, OverflowError):
            self._set_error()

    def square(self) -> None:
        try:
            x = self._get_current_number()
            self._set_from_float(x ** 2)
        except (ValueError, OverflowError):
            self._set_error()

    def cube(self) -> None:
        try:
            x = self._get_current_number()
            self._set_from_float(x ** 3)
        except (ValueError, OverflowError):
            self._set_error()

    def input_pi(self) -> None:
        # 현재 입력을 π로 대체
        self._cur = '{:.12g}'.format(math.pi)


class EngineeringCalculatorWindow(QWidget):
    """공학용 계산기 UI: 버튼 → EngineeringCalculator 매핑"""

    def __init__(self) -> None:
        super().__init__()
        self.engine = EngineeringCalculator()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle('Engineering Calculator')
        root = QVBoxLayout()
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        self.setLayout(root)

        # 표시부
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        font = QFont(self.display.font())
        font.setPointSize(26)
        self.display.setFont(font)
        self.display.setText(self.engine.display_text())
        root.addWidget(self.display)

        # 버튼 그리드(아이폰 공학 레이아웃을 참고)
        grid = QGridLayout()
        grid.setSpacing(6)
        root.addLayout(grid)

        rows = [
            ['2nd',  '(',     ')',     'mc',  'm+',   'AC', '+/-', '%',  '÷',  'Rad'],
            ['x²',   'x³',    'xʸ',    'eˣ',  '10ˣ', '7',  '8',  '9',  '×',  'Rand'],
            ['√x',   '∛x',    'ʸ√x',   'ln',  'log', '4',  '5',  '6',  '−',  'π'],
            ['sin',  'cos',   'tan',   'sinh','cosh','1',  '2',  '3',  '+',  'e'],
            ['sin⁻¹','cos⁻¹','tan⁻¹', 'tanh','EE',  '0',  '.',  '=',  '⌫',  ')'],
        ]

        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                btn = QPushButton(label)
                btn.setMinimumHeight(52)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked=False, ch=label: self.on_button(ch))
                grid.addWidget(btn, r, c)

        self.resize(760, 420)

    def on_button(self, ch: str) -> None:
        # 제어/표시 관련
        if ch == 'AC':
            self.engine.reset()
        elif ch == '+/-':
            self.engine.negative_positive()
        elif ch == '%':
            self.engine.percent()
        elif ch == '=':
            self.engine.equal()
        elif ch == '⌫':
            cur = self.engine.display_text()
            if cur and cur != '0':
                new = cur[:-1] or '0'
                # 엔진 내부 표시 갱신
                self.engine._cur = new
        elif ch == 'Rad' or ch == 'Deg':
            # 토글: 현재 라벨에 따라 전환
            use_rad = (ch == 'Rad')
            self.engine.set_angle_unit(use_rad)
            # 버튼 라벨 토글은 간단화를 위해 표시부에 안내만 표시(실제 버튼 라벨 토글은 생략)
            note = 'RAD' if use_rad else 'DEG'
            self.engine._cur = note

        # 숫자/점/괄호/연산자
        elif ch.isdigit():
            self.engine.input_digit(ch)
        elif ch == '.':
            self.engine.input_dot()
        elif ch in {'+', '−', '×', '÷'}:
            self.engine.set_operator(ch)
        elif ch in {'(', ')'}:
            # 간단 표시 누적(실제 파싱/계산은 확대 범위)
            cur = self.engine.display_text()
            self.engine._cur = ('0' if cur == '0' else cur) + ch

        # 공학 기능(요구 항목)
        elif ch == 'π':
            self.engine.input_pi()
        elif ch == 'x²':
            self.engine.square()
        elif ch == 'x³':
            self.engine.cube()
        elif ch == 'sin':
            self.engine.sin()
        elif ch == 'cos':
            self.engine.cos()
        elif ch == 'tan':
            self.engine.tan()
        elif ch == 'sinh':
            self.engine.sinh()
        elif ch == 'cosh':
            self.engine.cosh()
        elif ch == 'tanh':
            self.engine.tanh()

        # 그 외 추가 버튼은 이번 과제 범위에서 시각적 입력만 누적
        else:
            cur = self.engine.display_text()
            token = ch if ch in {'EE', 'Rand', 'ln', 'log', 'e', 'xʸ', 'eˣ', '10ˣ', '√x', '∛x', 'ʸ√x',
                                 'sin⁻¹', 'cos⁻¹', 'tan⁻¹'} else ch
            self.engine._cur = ('0' if cur == '0' else cur) + token

        self.display.setText(self.engine.display_text())


def main() -> None:
    app = QApplication(sys.argv)
    w = EngineeringCalculatorWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
