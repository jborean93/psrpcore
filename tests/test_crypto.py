# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

from psrpcore import _crypto as crypto


def test_key_exchange():
    session_key = b"\x00" * 16

    private, public = crypto.create_keypair()
    assert isinstance(private, crypto.rsa.RSAPrivateKey)
    assert isinstance(public, bytes)
    assert private.key_size == 2048

    enc_session_key = crypto.encrypt_session_key(public, session_key)
    assert isinstance(enc_session_key, bytes)
    assert enc_session_key.startswith(b"\x01\x02\x00\x00\x10\x66\x00\x00\x00\xa4\x00\x00")

    actual_session_key = crypto.decrypt_session_key(private, enc_session_key)
    assert actual_session_key == session_key

    data = b"abc"
    encryptor = crypto.PSRemotingCrypto()
    encryptor.register_key(actual_session_key)
    enc_data = encryptor.encrypt(data)
    assert enc_data != data

    dec_data = encryptor.decrypt(enc_data)
    assert dec_data == data
