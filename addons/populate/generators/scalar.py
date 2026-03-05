from .generator import Generator


class Boolean(Generator):
    """Generate random boolean values (``True``, ``False``, optionally ``None``)."""
    name = 'scalar.boolean'
    allowed_fields_type = ['boolean', 'virtual']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.unique:
            # It makes little sense to have a unique constraint on a boolean field
            raise ValueError(self.env._("Unique cannot be used with the boolean generator."))

        possible_values = [True, False]
        if not self.field.required:
            possible_values.append(None)

        invalid_values = [v for v in self.values if v not in possible_values]
        if invalid_values:
            raise ValueError(self.env._(
                "Invalid values %(invalid_values)s for %(field_type)s field. "
                "Allowed values are: %(possible_values)s.",
                invalid_values=invalid_values,
                field_type=self.field.type,
                possible_values=possible_values,
            ))

        if not self.values:
            self.values = possible_values

    def _next(self, known_vals):
        if self.should_generate_null():
            return False

        if self.has_weights:
            return self.rng.choices(self.values, weights=self.weights)[0]

        return self.rng.choice(self.values)


class Integer(Generator):
    """Generate random integers within a ``[start, end]`` range."""
    name = 'scalar.integer'
    allowed_fields_type = ['integer', 'virtual']

    def __init__(self, start: int = 1, end: int = 1000000, **kwargs):
        super().__init__(**kwargs)
        self.start = start
        self.end = end

    def _next(self, known_vals):
        if self.should_generate_null():
            return False

        if self.distribution:
            return self.distribution.sample_discrete(self.start, self.end)

        return self.rng.randint(self.start, self.end)

    @classmethod
    def get_kwargs(cls, attrs):
        kwargs = super().get_kwargs(attrs)
        kwargs.update(**{k: int(v) for k, v in attrs.items() if k in ('start', 'end')})
        return kwargs


class Float(Generator):
    """Generate random floats within a ``[start, end]`` range."""
    name = 'scalar.float'
    allowed_fields_type = ['float', 'virtual']

    def __init__(self, start: float = 1.0, end: float = 1000000.0, **kwargs):
        super().__init__(**kwargs)
        self.start = start
        self.end = end

    def _next(self, known_vals):
        if self.should_generate_null():
            return False

        if self.distribution:
            return self.distribution.sample_continuous(self.start, self.end)

        return self.rng.uniform(self.start, self.end)

    @classmethod
    def get_kwargs(cls, attrs):
        kwargs = super().get_kwargs(attrs)
        kwargs.update(**{k: float(v) for k, v in attrs.items() if k in ('start', 'end')})
        return kwargs
