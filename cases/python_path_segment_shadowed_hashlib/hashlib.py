class FakeDigest:
    def hexdigest(self) -> str:
        return "../outside"


def sha256(_value: bytes) -> FakeDigest:
    return FakeDigest()
