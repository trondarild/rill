from __future__ import absolute_import

from abc import ABCMeta, abstractmethod
import inspect
import collections
from collections import defaultdict
from types import NoneType

import schematics.types
import schematics.models

from future.utils import with_metaclass
from past.builtins import basestring

from rill.engine.exceptions import TypeHandlerError, PacketValidationError
from rill.utils import importable_class_name, locate_class

_type_handlers = []

# Mapping of native Python types to json types
# FIXME: str vs unicode
TYPE_MAP = {
    str: 'string',
    bool: 'boolean',
    int: 'int',
    float: 'number',
    complex: 'number',
    dict: 'object',
    list: 'array',
    tuple: 'array',
    # color
    # date
    # function
    # buffer
}

FBP_TYPES = {
    'any': {
        'color_id': 0
    },
    'string': {
        'color_id': 1
    },
    'boolean': {
        'color_id': 2
    },
    'int': {
        'color_id': 3
    },
    'number': {
        'color_id': 3
    },
    'object': {
        'color_id': 4
    },
    'array': {
        'color_id': 4
    },
}


class Stream(list):
    pass


def register_handler(cls):
    """
    Register a ``TypeHandler`` class

    Parameters
    ----------
    cls : Type[``TypeHandler``]
    """
    # LIFO
    _type_handlers.insert(0, cls)


def get_type_handler(type_def):
    """
    Givin a type definition, get an object for marshalling data of the specified
    type.

    Parameters
    ----------
    type_def : object
        instance stored on the `type` attribute of
        ``rill.engine.portdef.PortDefinition``

    Returns
    -------
    ``TypeHandler``
    """
    # if type_def is None:
    #     UnspecifiedTypeHandler(type_def)

    for cls in _type_handlers:
        if cls.claim_type_def(type_def):
            return cls(type_def)
        result = cls.claim_type(type_def)
        if result is not None:
            return cls(result)

    raise TypeHandlerError("Could not find type handler "
                           "for {!r}".format(type_def))


class TypeHandler(with_metaclass(ABCMeta, object)):
    """
    Base class for validating and serializing content.
    """
    def __init__(self, type_def):
        self.type_def = type_def

    @abstractmethod
    def is_any(self):
        raise NotImplementedError

    @abstractmethod
    def get_spec(self):
        """
        Get a fbp-protocol-compatible type spec

        Returns
        -------
        dict

        Raises
        ------
        ``rill.exceptions.TypeHandlerError``
        """
        raise NotImplementedError

    @abstractmethod
    def validate(self, value):
        """
        Validate `value`.

        Parameters
        ----------
        value

        Raises
        ------
        ``rill.exceptions.PacketValidationError``

        Returns
        -------
        object or None
            if non-None is returned, the returned value *may* replace the
            existing value in the packet, depending on where this is called
        """
        raise NotImplementedError

    @abstractmethod
    def to_primitive(self, data):
        """
        Convert data to a value safe to serialize.
        """
        raise NotImplementedError

    @abstractmethod
    def to_native(self, data):
        """
        Convert primitive data to its native Python construct.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def claim_type_def(cls, type_def):
        """
        Return whether the given type definition is compatible with this
        ``TypeHandler``.

        Parameters
        ----------
        type_def : object

        Returns
        -------
        bool
        """
        raise NotImplementedError

    @classmethod
    def claim_type(cls, typ):
        pass


class UnspecifiedTypeHandler(TypeHandler):

    def get_spec(self):
        return {'type': 'any'}

    def validate(self, value):
        return value

    def to_primitive(self, data):
        # this is assumed to be json-serializable
        return data

    def to_native(self, data):
        # this is assumed to be json-deserializable
        return data

    @classmethod
    def claim_type_def(cls, type_def):
        return False


# FIXME: Unused
class BasicTypeHandler(TypeHandler):
    """
    Simple type handler that is used when setting a port's `type` to a basic
    python type, such as `str`, `int`, `float`, or `bool`.

    This class provides no additional functionality when serializing data:
    the types are expected to be json-serializable.
    """
    def is_any(self):
        return False

    def get_spec(self):
        return {'type': TYPE_MAP.get(self.type_def, 'any')}

    def validate(self, value):
        if isinstance(value, self.type_def):
            return value
        try:
            # FIXME: we probably want a list of allowable types to cast from
            return self.type_def(value)
        except Exception as err:
            raise PacketValidationError(
                "Data is type {}: expected {}. Error while casting: {}".format(
                    value.__class__.__name__, self.type_def.__name__, err))

    def to_primitive(self, data):
        # this is assumed to be json-serializable
        return data

    def to_native(self, data):
        # this is assumed to be json-deserializable
        return data

    @classmethod
    def claim_type_def(cls, type_def):
        return inspect.isclass(type_def)


# register(BasicTypeHandler)


class SchematicsTypeHandler(TypeHandler):
    _type_lookup = {}
    _subtype_lookup = defaultdict(list)

    def __init__(self, type_def):
        if isinstance(type_def, schematics.types.BaseType):
            # nothing to do
            pass
        elif isinstance(type_def, schematics.models.Model):
            # for convenience we allow models to omit the ModelType wrapper
            type_def = schematics.types.ModelType(type_def)
        elif inspect.isclass(type_def) \
                and issubclass(type_def, schematics.types.BaseType):
            # for convenience we allow type classes to be passed without
            # instantiation:  e.g. type=StringType
            type_def = type_def()
        else:
            # handle type=str, type=int, etc
            result = self.claim_type(type_def)
            if result is not None:
                type_def = result
                if inspect.isclass(type_def):
                    type_def = type_def()
            else:
                # this should never happen
                raise TypeError("{} unsupported type".format(type_def))
        super(SchematicsTypeHandler, self).__init__(type_def)

    def is_any(self):
        return type(self.type_def) is schematics.types.BaseType

    def get_spec(self):
        if self.is_any():
            spec = {'type': 'any'}
        else:
            primitive_type = self.type_def.primitive_type
            spec = {'type': TYPE_MAP[primitive_type]}
            choices = self.type_def.choices
            if choices:
                spec['values'] = [self.to_primitive(c) for c in choices]
        return spec

    def validate(self, value):
        try:
            return self.type_def.to_native(value)
        except Exception as e:
            raise PacketValidationError(str(e))

    def to_primitive(self, data):
        if self.is_any():
            return serialize(data)
        else:
            return self.type_def.to_primitive(data)

    def to_native(self, data):
        return self.type_def.to_native(data)

    @staticmethod
    def is_schematics_obj(obj):
        bases = (schematics.types.BaseType, schematics.models.Model)
        return (isinstance(obj, bases) or
                (inspect.isclass(obj) and issubclass(obj, bases)))

    @classmethod
    def claim_type_def(cls, type_def):
        return cls.is_schematics_obj(type_def)

    @classmethod
    def claim_type(cls, typ):
        if not inspect.isclass(typ):
            return

        if typ in cls._type_lookup:
            return cls._type_lookup[typ]

        # go from deepest type to most basic type
        for depth in reversed(sorted(cls._subtype_lookup)):
            types = cls._subtype_lookup[depth]
            for check_type, schematics_type in types:
                if issubclass(typ, check_type):
                    # speed-up the next lookup
                    cls.register_type(typ, schematics_type)
                    return schematics_type

    @classmethod
    def register_type(cls, type, schematics_type, primitive_type=None,
                      allow_subclasses=False, overwrite=False):
        """
        Add to the list of known types.

        Parameters
        ----------
        type
        schematics_type
        primitive_type
        allow_subclasses

        Returns
        -------
        None
        """
        # assert that schematics_type is valid:
        if not (inspect.isclass(schematics_type) or
                issubclass(schematics_type, schematics.types.BaseType)):
            raise ValueError("schematics_type must be a BaseType "
                             "sub-class: {}".format(schematics_type))
        elif issubclass(schematics_type, schematics.types.CompoundType):
            raise ValueError("schematics_type must not be "
                             "compound: : {}".format(schematics_type))

        if not inspect.isclass(type):
            raise ValueError("type must be a class: {}".format(type))

        curr_primitive_type = getattr(schematics_type, 'primitive_type', None)
        if primitive_type is not None:
            if curr_primitive_type is not None:
                raise ValueError("{} already has a primitive_type".format(type))
            schematics_type.primitive_type = primitive_type
        elif curr_primitive_type is None:
            # FIXME: logger.warn()
            print("Registered schematics type {} does not have a "
                  "primitive_type attribute: this will lead to problems during "
                  "serialization".format(schematics_type))

        if not overwrite and type in cls._type_lookup:
            raise ValueError("tye {} is already registered".format(type))

        if allow_subclasses:
            cls._subtype_lookup[len(type.mro())].append((type, schematics_type))

        cls._type_lookup[type] = schematics_type


def serialize(obj):
    if isinstance(obj, collections.Mapping):
        newobj = collections.OrderedDict()
        for key, value in obj.iteritems():
            newobj[key] = serialize(value)
        return newobj
    elif isinstance(obj, (list, tuple)):
        return [serialize(x) for x in obj]
    else:
        obj_type = type(obj)
        handler = get_type_handler(obj_type)
        value = handler.to_primitive(obj)
        if obj_type in TYPE_MAP:
            return value

        location = importable_class_name(type(obj))
        # FIXME: store the schema separately?
        return {'__type__': location, 'value': value}


def deserialize(data):
    if isinstance(data, collections.Mapping):
        if '__type__' in data:
            typ = locate_class(data['__type__'])
            handler = get_type_handler(typ)
            print "deserializing", data['value'], handler.type_def
            return handler.to_native(data['value'])
        else:
            newobj = collections.OrderedDict()
            for key, value in data.iteritems():
                newobj[key] = deserialize(value)
            return newobj
    elif isinstance(data, (list, tuple)):
        return [deserialize(x) for x in data]
    else:
        # native json type
        return data


def _register_builtin_types():
    import decimal
    import datetime
    # temp fix until PR is merged
    schematics.types.IPv4Type.primitive_type = str
    schematics.types.IPv4Type.native_type = str
    schematics.types.StringType.primitive_type = str
    schematics.types.StringType.native_type = str
    schematics.types.URLType.primitive_type = str
    schematics.types.URLType.native_type = str
    schematics.types.EmailType.primitive_type = str
    schematics.types.EmailType.native_type = str
    schematics.types.IntType.primitive_type = int
    schematics.types.IntType.native_type = int
    schematics.types.FloatType.primitive_type = float
    schematics.types.FloatType.native_type = float
    schematics.types.DecimalType.primitive_type = str
    schematics.types.DecimalType.native_type = decimal.Decimal
    schematics.types.BooleanType.primitive_type = bool
    schematics.types.BooleanType.native_type = bool
    schematics.types.DateTimeType.primitive_type = str
    schematics.types.DateTimeType.native_type = datetime.datetime
    schematics.types.DateType.primitive_type = str
    schematics.types.DateType.native_type = datetime.date
    schematics.types.TimestampType.primitive_type = float
    schematics.types.TimestampType.native_type = datetime.timedelta
    schematics.types.ModelType.primitive_type = dict
    schematics.types.ListType.primitive_type = list
    schematics.types.DictType.primitive_type = dict

    SchematicsTypeHandler.register_type(int,
                                        schematics.types.IntType)
    SchematicsTypeHandler.register_type(bool,
                                        schematics.types.BooleanType)
    SchematicsTypeHandler.register_type(float,
                                        schematics.types.FloatType)
    SchematicsTypeHandler.register_type(basestring,
                                        schematics.types.StringType,
                                        allow_subclasses=True)
    SchematicsTypeHandler.register_type(decimal.Decimal,
                                        schematics.types.DecimalType)
    SchematicsTypeHandler.register_type(datetime.datetime,
                                        schematics.types.DateTimeType)
    SchematicsTypeHandler.register_type(datetime.date,
                                        schematics.types.DateType)
    SchematicsTypeHandler.register_type(NoneType,
                                        schematics.types.BaseType)


_register_builtin_types()
register_handler(SchematicsTypeHandler)
