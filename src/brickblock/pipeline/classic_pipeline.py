

class ClassicChain:
    
    def __init__(self):
        self.dict_knowledge = {}
    
    
    @staticmethod
    def new():
        return ClassicChain()
    
    def input(self, dict_value:dict):
        self.dict_knowledge['input'] = dict_value
        return self
    
    def function(self, func:function):
        self.dict_knowledge['function'] = func
        return self
    
    def 