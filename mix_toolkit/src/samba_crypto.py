"""Samba password helpers for the agreed reversible obfuscation rule."""


import base64
import sys



def __valid_pad_length(length):
    return 2 <= length <= 9


def decrypt_samba_password(password):
    if not password:
        raise ValueError("密码不能为空")

    token = str(password)
    if len(token) < 6:
        raise ValueError("密码值太短")

    tail = token[-2:]
    if not tail.isdigit():
        raise ValueError("密码值不包含有效的长度标记")

    prefix_length = int(tail[0]) + 1
    suffix_length = int(tail[1]) + 1
    if not __valid_pad_length(prefix_length) or not __valid_pad_length(suffix_length):
        raise ValueError("密码值包含无效的长度标记")

    payload = token[:-2]
    if len(payload) <= prefix_length + suffix_length:
        raise ValueError("密码值无效")

    reversed_b64 = payload[prefix_length:len(payload) - suffix_length]
    raw_b64 = reversed_b64[::-1]
    try:
        # return base64.b64decode(raw_b64, validate=True).decode("utf-8")
        if sys.version_info.major == 3:
            return str(base64.b64decode(bytes(raw_b64, encoding='utf-8')), encoding='utf-8')
        else:
            return str(base64.b64decode(bytes(raw_b64)))

    except Exception as exc:
        raise ValueError("Password value is not valid") from exc

if __name__ == "__main__":
    print(decrypt_samba_password('MC=M0RZdTXq0jZ/oiXCJnY0gkPH5mUU4Su3MZ817'))