import phonenumbers

class PhoneNumber(str):
    """Кастомный класс для валидации номера телефона"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, *args, **kwargs):
        if not isinstance(value, str):
            raise TypeError('Number is not a string value')
        try:
            phone = phonenumbers.parse(value)
            if not phonenumbers.is_valid_number(phone):
                raise ValueError('Invalid phone number')
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValueError('Invalid phone number format')
        return value