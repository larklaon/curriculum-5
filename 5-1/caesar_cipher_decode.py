def caesar_cipher_decode(target_text):
    results = []
    for shift in range(26):  # 알파벳 26글자
        decoded_text = ''
        for ch in target_text:
            if 'A' <= ch <= 'Z':
                decoded_text += chr((ord(ch) - ord('A') - shift) % 26 + ord('A'))
            elif 'a' <= ch <= 'z':
                decoded_text += chr((ord(ch) - ord('a') - shift) % 26 + ord('a'))
            else:
                decoded_text += ch
        print(f'[{shift:02d}] {decoded_text}')
        results.append(decoded_text)
    return results  # 인덱스=자리수

# 1) 암호문 읽기
with open('password.txt', 'r', encoding='utf-8') as f:
    cipher_text = f.read()

# 2) 전수 해독 출력
all_results = caesar_cipher_decode(cipher_text)

# 3) 사람이 식별한 자리수 입력 후 저장
k = int(input('정답으로 보이는 자리수를 입력하세요 (0~25): '))
with open('result.txt', 'w', encoding='utf-8') as f:
    f.write(all_results[k])

print('result.txt 저장 완료')
