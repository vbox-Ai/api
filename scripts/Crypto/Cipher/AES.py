# -*- coding: utf-8 -*-
"""
Crypto.Cipher.AES — pycryptodome 兼容层
底层使用 pyaes 纯 Python 实现 AES 加解密

兼容 API:
    from Crypto.Cipher import AES
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(data)
    decrypted = cipher.decrypt(data)

注意:
    - encrypt/decrypt 不自动填充, 由调用方处理 padding
    - 这与 pycryptodome 的行为一致 (pycryptodome 也不自动 pad)
    - 调用方需确保数据长度是 16 字节的整数倍
"""

import pyaes

# 模式常量 (与 pycryptodome 一致)
MODE_ECB = 1
MODE_CBC = 2
MODE_CFB = 3
MODE_OFB = 5
MODE_CTR = 6
MODE_OPENPGP = 7
MODE_CCM = 8
MODE_EAX = 9
MODE_SIV = 10
MODE_GCM = 11
MODE_OCB = 12
MODE_KW = 13
MODE_KWP = 14

# AES 参数
block_size = 16
key_size = (16, 24, 32)


class _AESCipher:
    """AES 加解密对象 — 兼容 pycryptodome 的 cipher 对象"""

    def __init__(self, key, mode, iv=None):
        self._key = key
        self._mode = mode
        self._iv = iv
        self.iv = iv  # pycryptodome 暴露 iv 属性

    def encrypt(self, plaintext):
        """
        加密 (不自动 padding, 调用方需确保数据是 16 字节整数倍)
        """
        if len(plaintext) % 16 != 0:
            raise ValueError("Data must be a multiple of 16 bytes")

        if self._mode == MODE_ECB:
            encrypter = pyaes.Encrypter(
                pyaes.AES(self._key), pyaes.MODE_ECB
            )
        elif self._mode == MODE_CBC:
            if self._iv is None:
                raise ValueError("CBC mode requires iv")
            encrypter = pyaes.Encrypter(
                pyaes.AES(self._key), pyaes.MODE_CBC, self._iv
            )
        else:
            raise ValueError("Unsupported mode: %d" % self._mode)

        # pyaes 的 feed 会自动加 PKCS7 padding, 我们不需要
        # 直接用底层 AES block 加密
        return self._encrypt_blocks(plaintext)

    def _encrypt_blocks(self, plaintext):
        """逐 block 加密, 不加 padding"""
        aes = pyaes.AES(self._key)
        result = bytearray()
        prev_block = bytearray(self._iv) if self._iv else None

        for i in range(0, len(plaintext), 16):
            block = bytearray(plaintext[i:i + 16])

            if self._mode == MODE_ECB:
                encrypted = aes.encrypt(block)
            elif self._mode == MODE_CBC:
                # XOR with previous block
                xored = bytearray(16)
                for j in range(16):
                    xored[j] = block[j] ^ prev_block[j]
                encrypted = aes.encrypt(xored)
                prev_block = encrypted
            else:
                encrypted = aes.encrypt(block)

            result.extend(encrypted)

        return bytes(result)

    def decrypt(self, ciphertext):
        """
        解密 (不自动 unpadding, 调用方需自行处理 PKCS7/ZeroPadding)
        """
        if len(ciphertext) % 16 != 0:
            raise ValueError("Data must be a multiple of 16 bytes")

        return self._decrypt_blocks(ciphertext)

    def _decrypt_blocks(self, ciphertext):
        """逐 block 解密, 不去 padding"""
        aes = pyaes.AES(self._key)
        result = bytearray()
        prev_block = bytearray(self._iv) if self._iv else None

        for i in range(0, len(ciphertext), 16):
            block = bytearray(ciphertext[i:i + 16])

            if self._mode == MODE_ECB:
                decrypted = aes.decrypt(block)
            elif self._mode == MODE_CBC:
                decrypted = aes.decrypt(block)
                # XOR with previous block
                xored = bytearray(16)
                for j in range(16):
                    xored[j] = decrypted[j] ^ prev_block[j]
                decrypted = xored
                prev_block = block
            else:
                decrypted = aes.decrypt(block)

            result.extend(decrypted)

        return bytes(result)


def new(key, mode, *args, **kwargs):
    """
    创建 AES cipher 对象 — 兼容 pycryptodome 的 AES.new()

    Args:
        key: 密钥 (16/24/32 字节)
        mode: 模式 (MODE_ECB / MODE_CBC)
        iv: 初始化向量 (CBC 模式需要, 16 字节)

    Returns:
        _AESCipher 对象
    """
    if len(key) not in key_size:
        raise ValueError("Incorrect AES key length (%d bytes)" % len(key))

    iv = kwargs.get('iv', None)
    if iv is not None:
        iv = bytes(iv) if not isinstance(iv, bytes) else iv
        if len(iv) != 16:
            raise ValueError("IV must be 16 bytes")

    if mode == MODE_CBC and iv is None:
        # pycryptodome 会自动生成随机 IV, 但蜘蛛脚本都会传入 iv
        # 这里也兼容自动生成
        import os
        iv = os.urandom(16)

    return _AESCipher(bytes(key) if not isinstance(key, bytes) else key, mode, iv)
