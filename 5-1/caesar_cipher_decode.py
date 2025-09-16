def caesar_cipher_decode(target_text):
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    length = len(alphabet)

    # 모든 시프트 값(0-25)에 대해 해독 시도
    for shift in range(length):
        decoded = ''
        for char in target_text:
            if char in alphabet:
                idx = alphabet.index(char)
                decoded += alphabet[(idx - shift) % length]
            else:
                decoded += char
        print(f'시프트 {shift}: {decoded}')
    
    # 사용자가 올바른 시프트 번호 선택
    while True:
        try:
            shift_num = int(input('해독에 알맞은 시프트 번호를 입력하세요 (0-25): '))
            if 0 <= shift_num < length:
                break
            else:
                print('0부터 25 사이의 숫자를 입력하세요.')
        except ValueError:
            print('숫자를 입력하세요.')
    
    # 선택한 시프트로 최종 해독 및 저장
    final_decoded = ''
    for char in target_text:
        if char in alphabet:
            idx = alphabet.index(char)
            final_decoded += alphabet[(idx - shift_num) % length]
        else:
            final_decoded += char
    
    try:
        with open('result.txt', 'w') as f:
            f.write(final_decoded)
        print('최종 해독 결과가 result.txt에 저장되었습니다.')
    except Exception as e:
        print('파일 저장 중 오류 발생:', e)


def read_password_file():
    try:
        with open('password.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print('password.txt 파일을 찾을 수 없습니다.')
        return ''
    except Exception as e:
        print('파일 읽기 중 오류 발생:', e)
        return ''


# 실행 코드
if __name__ == '__main__':
    encrypted_text = read_password_file()
    if encrypted_text:
        caesar_cipher_decode(encrypted_text)
