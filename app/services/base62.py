ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)

def encode(n: int) -> str:
    if n < 0:
        raise ValueError("Base62 encoding only supports non-negative integers")
    
    if n == 0:
        return ALPHABET[0]
    
    result = []
    
    while n > 0:
        n, remainder = divmod(n, BASE)
        result.append(ALPHABET[remainder])
        
    return "".join(reversed(result))

def decode(s: str) -> int:
    if not s:
        raise ValueError("Base62 string cannot be empty ")

    result = 0
    
    for char in s:
        if char not in ALPHABET:
            raise ValueError(f"Invalid Base62 character: {char}")
        
        result = result * BASE + ALPHABET.index(char)
        
    return result 