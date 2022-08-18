class UserInfo:
    def __init__(self, username: str, email: str,
                 firstname: str, lastname: str, **kwargs):
        self.username = username
        self.email = email
        self.firstname = firstname
        self.lastname = lastname