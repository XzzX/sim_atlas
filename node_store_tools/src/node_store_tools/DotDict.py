class DotDict(dict):
    """Dictionary with dot notation access to attributes."""

    def __init__(self, input_dict):
        super().__init__(input_dict)
        for key, value in input_dict.items():
            if isinstance(value, dict):
                value = DotDict(value)
            self[key] = value

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __dir__(self):
        """Enable autocompletion for dictionary keys."""
        return list(self.keys())

    def create_path(self, path: str):
        """
        Create a nested path of DotDict objects if it doesn't exist.

        This method takes a dot-separated path string and creates nested DotDict
        objects for each key in the path. If a key already exists, it navigates
        into it. If a key doesn't exist, it creates a new empty DotDict at that
        location.

        Args:
            path (str): A dot-separated string representing the path to create
                        (e.g., "level1.level2.level3").

        Returns:
            DotDict: The DotDict object at the end of the created path.

        Example:
            >>> store = DotDict({})
            >>> result = store.create_path("config.database.connection")
            >>> # Creates: {'config': {'database': {'connection': {}}}}
            >>> result  # Returns the innermost DotDict at 'connection'
        """
        key_list = path.split(".")
        current = self
        for key in key_list:
            if key not in current:
                current[key] = DotDict({})
            current = current[key]
        return current
