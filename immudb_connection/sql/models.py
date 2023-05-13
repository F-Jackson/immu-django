class SQLModel:
    def __init__(self, pks: list[str] = None, **kwargs):
        if pks is not None:
            self._pks = pks
            
        for key, value in kwargs.items():
            setattr(self, f'_{key}', value)
            
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(self, f'_{name}').copy()
    
    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            super().__setattr__(f'_{name}', value)
    
    def __delattr__(self, name):
        if name.startswith("_"):
            super().__delattr__(name)
        else:
            super().__delattr__(f'_{name}')
    
    def __str__(self):
        return str({k[1:]: getattr(self, k) for k in dir(self) if not k.startswith("__")})
    
    def __repr__(self):
        return str(self)
    
    def __dir__(self):
        return [k[1:] for k in dir(self) if not k.startswith("__")]
    
    @property
    def __pks__(self):
        return self._pks.copy()
    