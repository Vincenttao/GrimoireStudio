import string

class LexoRank:
    """
    Minimal LexoRank implementation for v1.5.
    Bucket is hardcoded to "0|".
    Format: "bucket|rank"
    """
    CHARS = string.digits + string.ascii_lowercase
    MIN_CHAR = CHARS[0]
    MAX_CHAR = CHARS[-1]

    @staticmethod
    def gen_between(rank_a: str, rank_b: str) -> str:
        """
        Generates a string that is lexicographically between rank_a and rank_b.
        Simple implementation: append middle chars.
        """
        # Strip bucket for calculation
        a = rank_a.split('|')[-1]
        b = rank_b.split('|')[-1]
        
        # Ensure a < b
        if a >= b:
            # Handle error or return something sensible
            return f"0|{a}z" 

        res = []
        i = 0
        while True:
            char_a = a[i] if i < len(a) else LexoRank.MIN_CHAR
            char_b = b[i] if i < len(b) else LexoRank.MAX_CHAR
            
            idx_a = LexoRank.CHARS.index(char_a)
            idx_b = LexoRank.CHARS.index(char_b)
            
            if idx_b - idx_a > 1:
                mid_idx = (idx_a + idx_b) // 2
                res.append(LexoRank.CHARS[mid_idx])
                break
            else:
                res.append(char_a)
                i += 1
                if i >= len(a) and i >= len(b):
                    res.append(LexoRank.CHARS[len(LexoRank.CHARS)//2])
                    break
        
        return f"0|{''.join(res)}"

    @staticmethod
    def gen_next(last_rank: str) -> str:
        """
        Append at the end.
        """
        base = last_rank.split('|')[-1]
        # Just increment the last char if possible, or append
        return f"0|{base}h"

lexorank = LexoRank()
