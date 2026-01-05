import threading
import functools
import time
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Generic, Tuple
from collections import OrderedDict

class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]

# mirror/primitive/metaclass.py
class LRUCacheMeta(type):
    """
    A metaclass that automatically adds LRU caching behavior to all method calls
    of the target class, similar to how template<typename T> works in C++.
    
    Usage:
        class MyClass(metaclass=LRUCacheMeta, maxsize=128):
            def my_method(self, x, y):
                # This method will be automatically LRU cached
                return x + y
    """
    
    def __new__(
        mcs: Type['LRUCacheMeta'],
        name: str,
        bases: Tuple[Type, ...],
        namespace: Dict[str, Any],
        maxsize: Optional[int] = None,
        **kwargs: Any
    ) -> Type:
        """
        Create a new class with LRU caching behavior.
        
        Args:
            name: The name of the class
            bases: Base classes
            namespace: Class namespace dictionary
            maxsize: Maximum size of the LRU cache (default: 128)
            **kwargs: Additional keyword arguments
        """
        # Get maxsize from kwargs or use default
        cache_size = maxsize if maxsize is not None else 128
        
        # Create cache data structures
        cache: OrderedDict[Any, Any] = OrderedDict()
        lock = threading.RLock()
        
        # Store original methods
        original_methods = {}
        
        def make_cache_key(method_name: str, *args: Any, **kwargs: Any) -> Tuple:
            """
            Create a cache key from method name, args, and kwargs.
            
            Args:
                method_name: Name of the method
                *args: Positional arguments
                **kwargs: Keyword arguments
                
            Returns:
                Tuple that can be used as a dictionary key
            """
            # Create a tuple of sorted kwargs items to ensure consistent hashing
            sorted_kwargs = tuple(sorted(kwargs.items())) if kwargs else ()
            return (method_name, args, sorted_kwargs)
        
        def lru_cache_wrapper(method: Callable, method_name: str) -> Callable:
            """
            Wrap a method with LRU caching behavior.
            
            Args:
                method: The original method
                method_name: Name of the method
                
            Returns:
                Wrapped method with LRU caching
            """
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Handle special case for 'self' parameter (first argument is instance)
                instance = args[0] if args else None
                key = make_cache_key(method_name, *args, **kwargs)
                
                with lock:
                    # Check if result is in cache
                    if key in cache:
                        # Move to end (most recently used)
                        cache.move_to_end(key)
                        return cache[key]
                
                # Compute result if not in cache
                result = method(*args, **kwargs)
                
                with lock:
                    # Add to cache
                    cache[key] = result
                    
                    # Remove least recently used if over capacity
                    if len(cache) > cache_size:
                        cache.popitem(last=False)
                
                return result
            
            # Copy method metadata
            wrapper.__name__ = method.__name__
            wrapper.__doc__ = method.__doc__
            wrapper.__module__ = method.__module__
            
            return wrapper
        
        # Wrap all callable methods (except magic methods)
        for attr_name, attr_value in list(namespace.items()):
            if callable(attr_value) and not attr_name.startswith('__'):
                # Store original method
                original_methods[attr_name] = attr_value
                # Replace with cached version
                namespace[attr_name] = lru_cache_wrapper(attr_value, attr_name)
        
        # Add cache management method
        def clear_cache(cls: Type) -> None:
            """Clear the entire LRU cache."""
            with lock:
                cache.clear()
        
        namespace['clear_cache'] = classmethod(clear_cache)
        
        # Add cache info method
        def cache_info(cls: Type) -> Dict[str, Any]:
            """Get information about the cache."""
            with lock:
                return {
                    'maxsize': cache_size,
                    'current_size': len(cache),
                    'full': len(cache) >= cache_size
                }
        
        namespace['cache_info'] = classmethod(cache_info)
        
        # Create the class
        cls = super().__new__(mcs, name, bases, namespace)
        
        # Store cache attributes on class
        cls._lru_cache = cache
        cls._lru_cache_lock = lock
        cls._lru_cache_size = cache_size
        return cls
