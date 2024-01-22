from typing import Any, Callable, Dict, List, Tuple, Type, Union
import inspect
 
DecoratorType = Callable[..., Type]

class LazyDecorator:
    def __init__(self) -> None:
        self.targets: Dict[Any, List[Tuple[Type, List[DecoratorType]]]] = {}

    def __call__(self, decorators: Union[List[DecoratorType], DecoratorType], group_key: Any = "default") -> Callable[[Type], Type]:
        if not isinstance(decorators, list):
            decorators = [decorators]
        
        for decorator in decorators:
            if not callable(decorator):
                raise TypeError("All elements in 'decorators' must be callable.")
        
        def wrapper(cls: Type) -> Type:
            self.targets.setdefault(group_key, []).append((cls, decorators))
            return cls
        
        return wrapper

    def __getitem__(self, group_key: Any) -> Callable:
        def apply_group(*args, **kwargs) -> None:
            for cls, decorators in self.targets.get(group_key, []):
                for decorator in decorators:
                    params = inspect.signature(decorator).parameters
                    filtered_kwargs = {k: v for k, v in kwargs.items() if k in params}
                    max_args = len(params) - 1 - len(filtered_kwargs)
                    filtered_args = args[:max_args]
                    
                    if len(filtered_args) + len(filtered_kwargs) < len(params) - 1:
                        raise TypeError("Not enough arguments for decorator.")
                    
                    cls = decorator(cls, *filtered_args, **filtered_kwargs)
        return apply_group
    
    def clear_group(self, group_key: Any) -> None:
        self.targets.pop(group_key, None)

if __name__ == '__main__':
    # Decorators
    def decoratorA(cls: Type) -> Type:
        cls.decoratorA = True
        return cls

    def decoratorB(cls: Type, param1: str, param2: str) -> Type:
        cls.decoratorB = f"{param1}_{param2}"
        return cls

    def decoratorC(param1: str) -> Callable[[Type], Type]:
        def actual_decorator(cls: Type) -> Type:
            cls.decoratorC = param1
            return cls
        return actual_decorator

    # Usage
    lazy_decorator = LazyDecorator()

    @lazy_decorator([decoratorA, decoratorB, decoratorC("closure_param")], "number")
    class Class1:
        pass

    # Later, apply decoration logic to all classes in a specific group
    lazy_decorator["number"]("x", "y", param1="z", param2="w")

    # Verify
    print(hasattr(Class1, "decoratorA"))  # Should print True
    print(hasattr(Class1, "decoratorB"))  # Should print True
    print(hasattr(Class1, "decoratorC"))  # Should print True

    print(Class1.decoratorB)  # Should print "z_w"
    print(Class1.decoratorC)  # Should print "closure_param"
