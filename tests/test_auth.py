from app.auth import hash_password, verify_password

def test_password_hashing():
    password = "secure_password_123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > 0

def test_password_verification_success():
    password = "secure_password_123"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True

def test_password_verification_failure():
    password = "secure_password_123"
    hashed = hash_password(password)
    
    assert verify_password("wrong_password", hashed) is False

def test_password_long_truncation():
    # bcrypt handles max 72 bytes. The function truncates.
    # We want to ensure that a password > 72 chars is handled gracefully 
    # and matches itself (truncated version) but not something else.
    
    long_password = "a" * 100
    hashed = hash_password(long_password)
    
    assert verify_password(long_password, hashed) is True
    
    # Should also match the truncated version
    truncated_password = "a" * 72
    assert verify_password(truncated_password, hashed) is True
    
    # Should not match a different 72 char string
    other_password = "b" * 72
    assert verify_password(other_password, hashed) is False
