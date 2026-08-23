from src.auth.security import (
    create_access_token,
    decode_access_token,
    generate_reset_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify_roundtrip():
    h = hash_password("s3cret!")
    assert h != "s3cret!"
    assert verify_password("s3cret!", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_roundtrip():
    token = create_access_token("user123", "a@b.com")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user123"
    assert payload["email"] == "a@b.com"


def test_decode_rejects_garbage_token():
    assert decode_access_token("not-a-real-token") is None


def test_reset_token_is_unique_and_url_safe():
    a = generate_reset_token()
    b = generate_reset_token()
    assert a != b
    assert len(a) > 20
