from rpcclient.exceptions import SymbolAbsentError


class SymbolsJar(dict):
    @staticmethod
    def create(client):
        """
        Factory method for creating symbols jars
        :param client: client
        :rtype: SymbolsJar
        """
        jar = SymbolsJar()
        jar.__dict__['_client'] = client
        return jar

    def get_lazy(self, name):
        client = self.__dict__['_client']
        s = client.dlsym(client._dlsym_global_handle, name)
        if 0 == s:
            raise SymbolAbsentError(f'no such loaded symbol: {name}')
        self[name] = client.symbol(s)
        return self[name]

    def __getitem__(self, item):
        if item not in self:
            symbol = self.get_lazy(item)
            if symbol:
                return symbol
        return dict.__getitem__(self, item)

    def __getattr__(self, name):
        if name not in self:
            client = self.__dict__['_client']
            s = client.dlsym(client._dlsym_global_handle, name)
            if 0 == s:
                raise SymbolAbsentError(f'no such loaded symbol: {name}')
            self[name] = client.symbol(s)
            return self[name]

        return self.get(name)

    def __setattr__(self, key, value):
        return self.__setitem__(key, value)

    def __delattr__(self, item):
        return self.__delitem__(item)

    def __sub__(self, other):
        retval = SymbolsJar.create(self.__dict__['_client'])
        for k1, v1 in self.items():
            if k1 not in other:
                retval[k1] = v1
        return retval

    def __add__(self, other):
        retval = SymbolsJar.create(self.__dict__['_client'])
        for k, v in other.items():
            retval[k] = v
        for k, v in self.items():
            retval[k] = v
        return retval
