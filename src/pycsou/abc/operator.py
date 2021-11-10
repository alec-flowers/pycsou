import numbers as nb
import types
import typing as typ

import numpy as np
import scipy.sparse.linalg as splin

import pycsou.runtime as pycrt
import pycsou.util as pycu

if pycu.deps.CUPY_ENABLED:
    import cupy as cp

NDArray = pycu.NDArray
ArrayModule = pycu.ArrayModule

__all__ = [
    "Property",
    "Apply",
    "Differential",
    "Gradient",
    "Adjoint",
    "Proximal",
    "SingledValued",
    "Map",
    "DiffMap",
    "Func",
    "DiffFunc",
    "ProxFunc",
    "LinFunc",
    "LinOp",
    "NormalOp",
    "SelfAdjointOp",
    "SquareOp",
    "UnitOp",
    "ProjOp",
    "OrthProjOp",
    "PosDefOp",
]


class Property:
    r"""
    Abstract base class for Pycsou's operators.
    """

    @classmethod
    def _property_list(cls) -> frozenset:
        r"""
        List all possible properties of Pycsou's base operators.

        Returns
        -------
        frozenset
            Set of properties.
        """
        return frozenset(
            ("apply", "_lipschitz", "jacobian", "_diff_lipschitz", "single_valued", "gradient", "prox", "adjoint")
        )

    @classmethod
    def properties(cls) -> typ.Set[str]:
        r"""
        List the properties of the class.

        Returns
        -------
        typ.Set[str]
            Set of available properties.

        Examples
        --------

        >>> import pycsou.abc.operator as pycop
        >>> for op in pycop._base_operators:
        ...     print(op, props)
        <class 'pycsou.abc.operator.Map'> {'apply'}
        <class 'pycsou.abc.operator.DiffMap'> {'apply', 'jacobian'}
        <class 'pycsou.abc.operator.DiffFunc'> {'gradient', 'apply', 'single_valued', 'jacobian'}
        <class 'pycsou.abc.operator.LinOp'> {'apply', 'adjoint', 'jacobian'}
        <class 'pycsou.abc.operator.Func'> {'apply', 'single_valued'}
        <class 'pycsou.abc.operator.ProxFunc'> {'apply', 'single_valued', 'prox'}
        <class 'pycsou.abc.operator.LinFunc'> {'apply', 'single_valued', 'jacobian', 'gradient', 'adjoint'}

        """
        props = set(dir(cls))
        return set(props.intersection(cls._property_list()))

    @classmethod
    def has(cls, prop: typ.Union[str, typ.Tuple[str, ...]]) -> bool:
        r"""
        Queries the class for certain properties.

        Parameters
        ----------
        prop: str | tuple(str)
            Queried properties.

        Returns
        -------
        bool
            ``True`` if the class has the queried properties, ``False`` otherwise.

        Examples
        --------

        >>> import pycsou.abc.operator as pycop
        >>> LinOp = pycop.LinOp
        >>> LinOp.has(('adjoint', 'jacobian'))
        True
        >>> LinOp.has(('adjoint', 'prox'))
        False
        """
        return set(prop) <= cls.properties()

    def __add__(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"],
        other: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"],
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        r"""
        Add two instances of :py:class:`~pycsou.abc.operator.Map` subclasses together (overloads the ``+`` operator).

        Parameters
        ----------
        self:  :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Left addend with shape (N,K).
        other: :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Right addend with shape (M,L).

        Returns
        -------
        :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Sum of ``self`` and ``other``.

        Raises
        ------
        NotImplementedError
            If other is not an instance of :py:class:`~pycsou.abc.operator.Map`.

        ValueError
            If the addends' shapes are inconsistent (see below).

        Notes
        -----

        The addends' shapes must be `consistent` with one another, that is, they must:

            * be `range-broadcastable`, i.e. ``N=M or 1 in (N,M)``.
            * have `identical domain sizes` except if at least one of the two addends is `domain-agnostic`, i.e. ``K=L or None in (K,L)``.

        The addends `needs not be` instances of the same :py:class:`~pycsou.abc.operator.Map` subclass. The sum output is an
        instance of one of the following :py:class:`~pycsou.abc.operator.Map` (sub)classes: :py:class:`~pycsou.abc.operator.Map`,
        :py:class:`~pycsou.abc.operator.DiffMap`, :py:class:`~pycsou.abc.operator.Func`, :py:class:`~pycsou.abc.operator.DiffFunc`,
        :py:class:`~pycsou.abc.operator.ProxFunc`, :py:class:`~pycsou.abc.operator.LinOp`, or :py:class:`~pycsou.abc.operator.LinFunc`.
        The output type is determined automatically by inspecting the shapes and common properties of the two addends as per the following table
        (the other half of the table can be filled by symmetry due to the commutativity of the addition):

        +----------+-----+---------+------+----------+----------+---------+----------+
        |          | Map | DiffMap | Func | DiffFunc | ProxFunc | LinOp   | LinFunc  |
        +==========+=====+=========+======+==========+==========+=========+==========+
        | Map      | Map | Map     | Map  | Map      | Map      | Map     | Map      |
        +----------+-----+---------+------+----------+----------+---------+----------+
        | DiffMap  |     | DiffMap | Map  | DiffMap  | Map      | DiffMap | DiffMap  |
        +----------+-----+---------+------+----------+----------+---------+----------+
        | Func     |     |         | Func | Func     | Func     | Map     | Func     |
        +----------+-----+---------+------+----------+----------+---------+----------+
        | DiffFunc |     |         |      | DiffFunc | Func     | DiffMap | DiffFunc |
        +----------+-----+---------+------+----------+----------+---------+----------+
        | ProxFunc |     |         |      |          | Func     | Map     | ProxFunc |
        +----------+-----+---------+------+----------+----------+---------+----------+
        | LinOp    |     |         |      |          |          | LinOp   | LinOp    |
        +----------+-----+---------+------+----------+----------+---------+----------+
        | LinFunc  |     |         |      |          |          |         | LinFunc  |
        +----------+-----+---------+------+----------+----------+---------+----------+

        If the sum has one or more of the following properties ``[apply, jacobian, gradient, adjoint, _lipschitz, _diff_lipschitz]``,
        the latter are defined as the sum of the corresponding properties of the addends. In the case ``ProxFunc + LinFunc``,
        the ``prox`` property is updated as described in the method ``__add__`` of the subclass :py:class:`~pycsou.abc.operator.ProxFunc`.

        .. Hint::

            Note that the case ``ProxFunc + LinFunc`` is handled in the methods ``__add__`` of the subclasses :py:class:`~pycsou.abc.operator.ProxFunc`
            and :py:class:`~pycsou.abc.operator.LinFunc`.

        """
        if not isinstance(other, Map):
            raise NotImplementedError(f"Cannot add object of type {type(self)} with object of type {type(other)}.")
        try:
            out_shape = pycu.infer_sum_shape(self.shape, other.shape)
        except ValueError:
            raise ValueError(f"Cannot sum two maps with inconsistent shapes {self.shape} and {other.shape}.")
        shared_props = self.properties() & other.properties()
        shared_props.discard("prox")
        for Op in _base_operators:
            if Op.properties() == shared_props:
                break
        if Op in [LinOp, DiffFunc, LinFunc]:
            shared_props.discard("jacobian")
        shared_props.discard("single_valued")
        out_op = Op(out_shape)
        for prop in shared_props:
            if prop in ["_lispchitz", "_diff_lipschitz"]:
                setattr(out_op, prop, getattr(self, prop) + getattr(other, prop))
            else:

                @pycrt.enforce_precision(i="arr", o=False)  # Decorate composite method to avoid recasting [arr] twice.
                def composite_method(obj, arr: NDArray) -> typ.Union[NDArray, "LinOp"]:
                    return getattr(self, prop)(arr) + getattr(other, prop)(arr)

                setattr(out_op, prop, types.MethodType(composite_method, out_op))
        return out_op.squeeze()

    def __mul__(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"],
        other: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc", nb.Real],
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        r"""
        Scale/compose one/two instance(s) of :py:class:`~pycsou.abc.operator.Map` subclasses respectively (overloads the ``*`` operator).

        Parameters
        ----------
        self: :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Left factor with shape (N,K).
        other: :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Right factor. Should be a real scalar or an instance of :py:class:`~pycsou.abc.operator.Map` subclasses with shape (M,L).

        Returns
        -------
        :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Product (scaling or composition) of ``self`` with ``other``, with shape (N,K) (for scaling) or (N,L) (for composition).

        Raises
        ------
        NotImplementedError
            If other is not an instance of :py:class:`~pycsou.abc.operator.Map` or :py:class:`numbers.Real`.

        ValueError
            If the factors' shapes are inconsistent (see below).

        Notes
        -----

        The factors' shapes must be `consistent` with one another, that is ``K=M``. If the left factor is domain-agnostic
        (i.e. ``K=None``) then ``K!=M`` is allowed. The right factor can also be domain-agnostic, in which case the output
        is also domain-agnostic and has shape (N, None).


        The factors `needs not be` instances of the same :py:class:`~pycsou.abc.operator.Map` subclass. The product output is an
        instance of one of the following :py:class:`~pycsou.abc.operator.Map` (sub)classes: :py:class:`~pycsou.abc.operator.Map`,
        :py:class:`~pycsou.abc.operator.DiffMap`, :py:class:`~pycsou.abc.operator.Func`, :py:class:`~pycsou.abc.operator.DiffFunc`,
        :py:class:`~pycsou.abc.operator.ProxFunc`, :py:class:`~pycsou.abc.operator.LinOp`, or :py:class:`~pycsou.abc.operator.LinFunc`.
        The output type is determined automatically by inspecting the shapes and common properties of the two factors as per the following table:

        +----------+---------+----------+------+----------+----------+-------------+----------+
        |          | Map     | DiffMap  | Func | DiffFunc | ProxFunc | LinOp       | LinFunc  |
        +==========+=========+==========+======+==========+==========+=============+==========+
        | Map      | Map     | Map      | Map  | Map      | Map      | Map         | Map      |
        +----------+---------+----------+------+----------+----------+-------------+----------+
        | DiffMap  | Map     | DiffMap  | Map  | DiffMap  | Map      | DiffMap     | DiffMap  |
        +----------+---------+----------+------+----------+----------+-------------+----------+
        | Func     | Func    | Func     | Func | Func     | Func     | Func        | Func     |
        +----------+---------+----------+------+----------+----------+-------------+----------+
        | DiffFunc | Func    | DiffFunc | Func | DiffFunc | Func     | DiffFunc    | DiffFunc |
        +----------+---------+----------+------+----------+----------+-------------+----------+
        | ProxFunc | Func    | Func     | Func | Func     | Func     | Func        | Func     |
        +----------+---------+----------+------+----------+----------+-------------+----------+
        | LinOp    | Map     | DiffMap  | Map  | DiffMap  | Map      | LinOp       | LinOp    |
        +----------+---------+----------+------+----------+----------+-------------+----------+
        | LinFunc  | LinFunc | DiffFunc | Func | DiffFunc | Func     | LinFunc     | LinFunc  |
        +----------+---------+----------+------+----------+----------+-------------+----------+


        If the product output has one or more of the following properties ``[apply, jacobian, gradient, adjoint, _lipschitz, _diff_lipschitz]``,
        the latter are defined from the corresponding properties of the factors as follows (the pseudocode below is mathematically equivalent to but does
        not necessarily reflect the actual implementation):

        .. code-block:: python3

            prod._lipschitz = self._lipschitz * other._lipschitz
            prod.apply = lambda x: self.apply(other.apply(x))
            prod.jacobian = lambda x: self.jacobian(other.apply(x)) * other.jacobian(x)
            prod.gradient = lambda x: other.jacobian(x).adjoint(self.gradient(other.apply(x)))
            prod.adjoint = lambda x: other.adjoint(self.adjoint(x))

        where ``prod = self * other`` denotes the product of ``self`` with ``other``.
        Moreover, the (potential) attribute :py:attr:`~pycsou.abc.operator.DiffMap._diff_lipschitz` is updated as follows:

        .. code-block:: python3

            if isinstance(self, LinOp):
                prod._diff_lipschitz = self._lipschitz * other._diff_lipschitz
            elif isinstance(other, LinOp):
                prod._diff_lipschitz = self._diff_lipschitz * (other._lipschitz) ** 2
            else:
                prod._diff_lipschitz = np.infty

        Unlike the other properties listed above, automatic update of the :py:attr:`~pycsou.abc.operator.DiffMap._diff_lipschitz` attribute is
        hence only possible when either ``self`` or ``other`` is a :py:class:`~pycsou.abc.operator.LinOp` (otherwise it is set to its default value ``np.infty``).

        .. Hint::

            The case ``ProxFunc * LinOp`` yields in general a :py:class:`~pycsou.abc.operator.Func` object except when
            the :py:class:`~pycsou.abc.operator.LinOp` factor is of type :py:class:`~pycsou.abc.operator.UnitOp` where it returns
            a :py:class:`~pycsou.abc.operator.ProxFunc` (see :py:meth:`~pycsou.abc.operator.__mul__` of :py:class:`~pycsou.abc.operator.ProxFunc` for more).
            This case, together with the case ``ProxFunc * scalar`` are handled separately in the method :py:meth:`~pycsou.abc.operator.__mul__` of the subclass :py:class:`~pycsou.abc.operator.ProxFunc`,
            where the product's ``prox`` property update is described.
        """
        if isinstance(other, nb.Real):
            from pycsou.linop.base import HomothetyOp

            hmap = HomothetyOp(other, dim=self.shape[0])
            return hmap.__mul__(self)
        elif not isinstance(other, Map):
            raise NotImplementedError(f"Cannot multiply object of type {type(self)} with object of type {type(other)}.")
        try:
            out_shape = pycu.infer_composition_shape(self.shape, other.shape)
        except ValueError:
            raise ValueError(f"Cannot compose two maps with inconsistent shapes {self.shape} and {other.shape}.")
        shared_props = self.properties() & other.properties()
        shared_props.discard("prox")
        if self.shape[0] == 1 and "jacobian" in shared_props:
            shared_props.update({"gradient", "single_valued"})
        for Op in _base_operators:
            if Op.properties() == shared_props:
                break
        if Op in [LinOp, DiffFunc, LinFunc]:
            shared_props.discard("jacobian")
        shared_props.discard("single_valued")
        out_op = Op(out_shape)
        for prop in shared_props:  # ("apply", "_lipschitz", "jacobian", "_diff_lipschitz", "gradient", "adjoint")
            if prop == "apply":
                out_op.apply = types.MethodType(lambda obj, arr: self.apply(other.apply(arr)), out_op)
            elif prop == "_lipschitz":
                out_op._lipschitz = self._lipschitz * other._lipschitz
            elif prop == "_diff_lipschitz":
                if isinstance(self, LinOp):
                    out_op._diff_lipschitz = self._lipschitz * other._diff_lipschitz
                elif isinstance(other, LinOp):
                    out_op._diff_lipschitz = self._diff_lipschitz * (other._lipschitz) ** 2
                else:
                    out_op._diff_lipschitz = np.infty
            elif prop == "gradient":

                @pycrt.enforce_precision(i="arr")
                def composite_gradient(obj, arr: NDArray) -> NDArray:
                    return other.jacobian(arr).adjoint(self.gradient(other.apply(arr)))

                out_op.gradient = types.MethodType(composite_gradient, out_op)
            elif prop == "jacobian":

                @pycrt.enforce_precision(i="arr", o=False)
                def composite_jacobian(obj, arr: NDArray) -> "LinOp":
                    return self.jacobian(other.apply(arr)) * other.jacobian(arr)

                out_op.jacobian = types.MethodType(composite_jacobian, out_op)
            elif prop == "adjoint":
                out_op.adjoint = types.MethodType(lambda obj, arr: other.adjoint(self.adjoint(arr)), out_op)
        return out_op.squeeze()

    def __rmul__(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"], other: nb.Real
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        r"""
        Scale an instance of :py:class:`~pycsou.abc.operator.Map` subclasses by multiplying it from the left with a real number, i.e. ``prod = scalar * self``.

        Parameters
        ----------
        other: numbers.Real
            Left scaling factor.

        Returns
        -------
        :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Scaled operator.
        """
        return self.__mul__(other)

    def __pow__(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"], power: int
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "LinOp", "LinFunc"]:
        r"""
        Exponentiate (i.e. compose with itself) an instance of :py:class:`~pycsou.abc.operator.Map` subclasses ``power`` times (overloads the ``**`` operator).

        Parameters
        ----------
        power: int
            Exponentiation power (number of times the operator is composed with itself).

        Returns
        -------
        :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Exponentiated operator.
        """
        if type(power) is int:
            if power == 0:
                from pycsou.linop.base import IdentityOperator

                exp_map = IdentityOperator(shape=self.shape)
            else:
                exp_map = self
                for i in range(1, power):
                    exp_map = self.__mul__(exp_map)
            return exp_map
        else:
            raise NotImplementedError

    def __neg__(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        r"""
        Negate a map (overloads the ``-`` operator). Alias for ``self.__mul__(-1)``.
        """
        return self.__mul__(-1)

    def __sub__(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"],
        other: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"],
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "LinOp", "LinFunc"]:
        r"""
        Take the difference between two instances of :py:class:`~pycsou.abc.operator.Map` subclasses. Alias for ``self.__add__(other.__neg__())``.

        Parameters
        ----------
        self: :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Left term of the subtraction with shape (N,K).
        other: :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Right term of the subtraction with shape (M,L).

        Returns
        -------
        :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Difference between ``self`` and ``other``.
        """
        return self.__add__(other.__neg__())

    def __truediv__(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"], scalar: nb.Real
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        r"""
        Divides a map by a real ``scalar`` (overloads the ``/`` operator). Alias for ``self.__mul__(1 / scalar)``.
        """
        if isinstance(scalar, nb.Real):
            return self.__mul__(1 / scalar)
        else:
            raise NotImplementedError

    def argscale(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"],
        scalar: nb.Real,
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        r"""
        Dilate/shrink the domain of an instance of :py:class:`~pycsou.abc.operator.Map` subclasses.

        Parameters
        ----------
        scalar: numbers.Real
            Dilation/shrinking factor.

        Returns
        -------
        :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Domain-rescaled operator.

        Raises
        ------
        NotImplementedError
            If scalar is not a real number.

        Notes
        -----
        Calling ``self.argscale(scalar)`` is equivalent to precomposing ``self`` with the (unitary) linear operator :py:class:`~pycsou.linop.base.HomotethyOp`:

        .. code-block:: python3

            # The two statements below are functionally equivalent
            out1 = self.argscale(scalar)
            out2 = self * HomotethyOp(scalar, dim=self.shape[1])

        """
        if isinstance(scalar, nb.Real):
            from pycsou.linop.base import HomothetyOp

            hmap = HomothetyOp(scalar, dim=self.shape[1])
            return self.__mul__(hmap)
        else:
            raise NotImplementedError

    @pycrt.enforce_precision(i="arr", o=False)
    def argshift(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"], arr: NDArray
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        r"""
        Domain-shift an instance of :py:class:`~pycsou.abc.operator.Map` subclasses by ``arr``.

        Parameters
        ----------
        arr: NDArray
            Shift vector with size (N,).

        Returns
        -------
        :py:class:`~pycsou.abc.operator.Map` | :py:class:`~pycsou.abc.operator.DiffMap` | :py:class:`~pycsou.abc.operator.Func` | :py:class:`~pycsou.abc.operator.DiffFunc` | :py:class:`~pycsou.abc.operator.ProxFunc` | :py:class:`~pycsou.abc.operator.LinOp` | :py:class:`~pycsou.abc.operator.LinFunc`
            Domain-shifted operator.

        Raises
        ------
        ValueError
            If ``arr`` is not of type NDArray of has incorrect size, i.e. ``N != self.shape[1]``.

        Notes
        -----
        The output domain-shifted operator has either the same type of ``self`` or is of type
        :py:class:`~pycsou.abc.operator.DiffMap`/:py:class:`~pycsou.abc.operator.DiffFunc` when ``self`` is a
        :py:class:`~pycsou.abc.operator.LinOp`/:py:class:`~pycsou.abc.operator.LinFunc` object respectively (shifting does not preserve linearity).
        Moreover, if the output has one or more of the following properties ``[apply, jacobian, gradient, prox, _lipschitz, _diff_lipschitz]``,
        the latter are defined from the corresponding properties of ``self`` as follows (the pseudocode below is mathematically equivalent to but does
        not necessarily reflect the actual implementation):

        .. code-block:: python3

            out._lipschitz = self._lipschitz
            out._diff_lipschitz = self._diff_lipschitz
            out.apply = lambda x: self.apply(x + arr)
            out.jacobian = lambda x: self.jacobian(x + arr)
            out.gradient = lambda x: self.gradient(x + arr)
            out.prox = lambda x, tau: self.prox(x + arr, tau) - arr

        where ``out = self.argshift(arr)`` denotes the domain-shifted output.


        """
        try:
            arr = arr.copy().squeeze()
        except:
            raise ValueError("Argument [arr] must be of type NDArray.")
        if (self.shape[-1] is None) or (self.shape[-1] == arr.shape[-1]):
            out_shape = (self.shape[0], arr.shape[-1])
        else:
            raise ValueError(f"Invalid lag shape: {arr.shape[-1]} != {self.shape[-1]}")
        if isinstance(self, LinFunc):  # Shifting a linear map makes it an affine map.
            out_op = DiffFunc(shape=out_shape)
        elif isinstance(self, LinOp):  # Shifting a linear map makes it an affine map.
            out_op = DiffMap(shape=out_shape)
        else:
            out_op = self.__class__(shape=out_shape)
        props = out_op.properties()
        if out_op == DiffFunc:
            props.discard("jacobian")
        props.discard("single_valued")
        for prop in out_op.properties():
            if prop in ["_lispchitz", "_diff_lipschitz"]:
                setattr(out_op, prop, getattr(self, prop))
            elif prop == "prox":
                out_op.prox = types.MethodType(lambda obj, x, tau: self.prox(x + arr, tau) - arr, out_op)
            else:

                def argshifted_method(obj, x: NDArray) -> typ.Union[NDArray, "LinOp"]:
                    return getattr(self, prop)(x + arr)

                setattr(out_op, prop, types.MethodType(argshifted_method, out_op))
        return out_op.squeeze()


class SingledValued(Property):
    def single_valued(self):
        return True


class Apply(Property):
    @pycrt.enforce_precision(i="arr")
    def __call__(self, arr: NDArray) -> NDArray:
        return self.apply(arr)

    def apply(self, arr: NDArray) -> NDArray:
        raise NotImplementedError

    def lipschitz(self) -> float:
        raise NotImplementedError


class Differential(Property):
    def diff_lipschitz(self) -> float:
        raise NotImplementedError

    def jacobian(self, arr: NDArray) -> "LinOp":
        raise NotImplementedError


class Gradient(Differential):
    @pycrt.enforce_precision(i="arr", o=False)
    def jacobian(self, arr: NDArray) -> "LinOp":
        from pycsou.linop.base import ExplicitLinFunc

        return ExplicitLinFunc(self.gradient(arr))

    def gradient(self, arr: NDArray) -> NDArray:
        raise NotImplementedError


class Adjoint(Property):
    def adjoint(self, arr: NDArray) -> NDArray:
        raise NotImplementedError


class Proximal(Property):
    def prox(self, arr: NDArray, tau: float) -> NDArray:
        raise NotImplementedError

    @pycrt.enforce_precision(i=("arr", "sigma"), o=True)
    def fenchel_prox(self, arr: NDArray, sigma: float) -> NDArray:
        return arr - sigma * self.prox(arr=arr / sigma, tau=1 / sigma)


class Map(Apply):
    def __init__(self, shape: typ.Tuple[int, typ.Union[int, None]]):
        if len(shape) > 2:
            raise NotImplementedError(
                "Shapes of map objects must be tuples of length 2 (tensorial maps not supported)."
            )
        elif shape[0] is None:
            raise ValueError("Codomain agnostic maps are not supported.")
        self._shape = shape
        self._lipschitz = np.infty

    @property
    def shape(self):
        return self._shape

    @property
    def dim(self):
        return self.shape[1]

    @property
    def codim(self):
        return self.shape[0]

    def squeeze(self) -> typ.Union["Map", "Func"]:
        return self._squeeze(out=Func)

    def _squeeze(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"],
        out: typ.Type[typ.Union["Func", "DiffFunc", "LinFunc"]],
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        if self.shape[0] == 1:
            obj = self.specialize(cast_to=out)
        else:
            obj = self
        return obj

    def lipschitz(self) -> float:
        return self._lipschitz

    def specialize(
        self: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"],
        cast_to: typ.Union[type, typ.Type["Property"]],
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        if cast_to == self.__class__:
            obj = self
        else:
            if self.properties() > cast_to.properties():
                raise ValueError(
                    f"Cannot specialize an object of type {self.__class__} to an object of type {cast_to}."
                )
            obj = cast_to(self.shape)
            for prop in self.properties():
                if prop == "jacobian" and cast_to.has("single_valued"):
                    obj.gradient = types.MethodType(lambda _, x: self.jacobian(x).asarray().reshape(-1), obj)
                else:
                    setattr(obj, prop, getattr(self, prop))
        return obj


class DiffMap(Map, Differential):
    def __init__(self, shape: typ.Tuple[int, typ.Union[int, None]]):
        super(DiffMap, self).__init__(shape)
        self._diff_lipschitz = np.infty

    def squeeze(self) -> typ.Union["DiffMap", "DiffFunc"]:
        return self._squeeze(out=DiffFunc)

    def diff_lipschitz(self) -> float:
        return self._diff_lipschitz


class Func(Map, SingledValued):
    def __init__(self, shape: typ.Union[typ.Union[int, None], typ.Tuple[int, typ.Union[int, None]]]):
        shape = tuple(shape)
        if len(shape) == 1:
            shape = (1,) + shape
        else:
            if shape[0] > 1:
                raise ValueError("Functionals" " must be of the form (1,n).")
        super(Func, self).__init__(shape)


class ProxFunc(Func, Proximal):
    def __init__(self, shape: typ.Union[typ.Union[int, None], typ.Tuple[int, typ.Union[int, None]]]):
        super(ProxFunc, self).__init__(shape)

    def __add__(
        self: "ProxFunc", other: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        f = Property.__add__(self, other)
        if isinstance(other, LinFunc):
            f = f.specialize(cast_to=ProxFunc)
            f.prox = types.MethodType(lambda _, x, tau: self.prox(x - tau * other.asarray(), tau), f)
        return f.squeeze()

    def __mul__(
        self: "ProxFunc",
        other: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc", "HomothetyOp"],
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        f = Property.__mul__(self, other)
        if isinstance(other, UnitOp):
            f.specialize(cast_to=ProxFunc)
            f.prox = types.MethodType(lambda obj, arr, tau: other.adjoint(self.prox(other.apply(arr), tau)), f)
        elif isinstance(other, HomothetyOp):
            f.specialize(cast_to=ProxFunc)
            f.prox = types.MethodType(
                lambda obj, arr, tau: (1 / other._cst) * self.prox(other._cst * arr, tau * (other._cst) ** 2), f
            )
        return f.squeeze()


class DiffFunc(Func, Gradient):
    def __init__(self, shape: typ.Union[typ.Union[int, None], typ.Tuple[int, typ.Union[int, None]]]):
        super(DiffFunc, self).__init__(shape)


class LinOp(DiffMap, Adjoint):
    def __init__(self, shape: typ.Tuple[int, typ.Union[int, None]]):
        super(LinOp, self).__init__(shape)
        self._diff_lipschitz = 0

    def squeeze(self) -> typ.Union["LinOp", "LinFunc"]:
        return self._squeeze(out=LinFunc)

    def jacobian(self, arr: NDArray) -> "LinOp":
        return self

    @property
    def T(self) -> "LinOp":
        adj = LinOp(shape=self.shape[::-1])
        adj.apply = self.adjoint
        adj.adjoint = self.apply
        adj._lipschitz = self._lipschitz
        return adj

    def to_scipy_operator(self, dtype: typ.Optional[type] = None, gpu: bool = False) -> splin.LinearOperator:
        def matmat(arr: NDArray) -> NDArray:
            return self.apply(arr.transpose())

        def rmatmat(arr: NDArray) -> NDArray:
            return self.adjoint(arr.transpose())

        if dtype is None:
            dtype = pycrt.getPrecision().value

        if (
            pycu.deps.CUPY_ENABLED and gpu
        ):  # Scipy casts any input to the LinOp as a Numpy array so the cupyx version is needed.
            import cupyx.scipy.sparse.linalg as spx
        else:
            spx = splin
        return spx.LinearOperator(
            shape=self.shape, matvec=self.apply, rmatvec=self.adjoint, matmat=matmat, rmatmat=rmatmat, dtype=dtype
        )

    def lipschitz(self, recompute: bool = False, gpu: bool = False, **kwargs):  # Add trace estimate
        if recompute or (self._lipschitz == np.infty):
            kwargs.update(dict(k=1, which="LM", gpu=gpu))
            self._lipschitz = self.svdvals(**kwargs)
        return self._lipschitz

    @pycrt.enforce_precision(o=True)
    def svdvals(self, k: int, which="LM", gpu: bool = False, **kwargs) -> NDArray:
        kwargs.update(dict(k=k, which=which, return_singular_vectors=False))
        SciOp = self.to_scipy_operator(pycrt.getPrecision().value, gpu=gpu)
        if pycu.deps.CUPY_ENABLED and gpu:
            import cupyx.scipy.sparse.linalg as spx
        else:
            spx = splin
        return spx.svds(SciOp, **kwargs)

    def asarray(self, xp: ArrayModule = np, dtype: typ.Optional[type] = None) -> NDArray:
        if dtype is None:
            dtype = pycrt.getPrecision().value
        return self.apply(xp.eye(self.shape[1], dtype=dtype))

    def __array__(self, dtype: typ.Optional[type] = None) -> np.ndarray:
        if dtype is None:
            dtype = pycrt.getPrecision().value
        return self.asarray(xp=np, dtype=dtype)

    def gram(self) -> "LinOp":
        return self.T * self

    def cogram(self) -> "LinOp":
        return self * self.T

    @pycrt.enforce_precision(i="arr")
    def pinv(
        self, arr: NDArray, damp: typ.Optional[float] = None, verbose: typ.Optional[int] = None, **kwargs
    ) -> NDArray:  # Should we have a decorator that performs trivial vectorization like that for us?
        if arr.ndim == 1:
            return self._pinv(arr=arr, damp=damp, verbose=verbose, **kwargs)
        else:
            xp = pycu.get_array_module(arr)
            pinv1d = lambda x: self._pinv(arr=x, damp=damp, verbose=verbose, **kwargs)
            return xp.apply_along_axis(func1d=pinv1d, arr=arr, axis=-1)

    def _pinv(
        self, arr: NDArray, damp: typ.Optional[float] = None, verbose: typ.Optional[int] = None, **kwargs
    ) -> NDArray:
        """
        The routines scipy.sparse.linalg.lsqr or scipy.sparse.linalg.lsmr offer the same functionality as this routine
        but may converge faster when the operator is ill-conditioned and/or when there is no fast algorithm for self.gram()
        (i.e. when self.gram() is trivially evaluated as the composition self.T * self). The latter are however not available
        in matrix-free form on GPUs.
        """
        from pycsou.linop.base import IdentityOperator

        b = self.adjoint(arr)
        if damp is not None:
            damp = np.array(damp, dtype=arr.dtype).item()  # cast to correct type
            A = self.gram() + damp * IdentityOperator(shape=(self.shape[1], self.shape[1]))
        else:
            A = self.gram()
        if "x0" not in kwargs:
            kwargs["x0"] = 0 * arr
        if "atol" not in kwargs:
            kwargs["atol"] = 1e-16
        if verbose is not None:

            class CallBack:
                def __init__(self, verbose: int, A: LinOp, b: NDArray):
                    self.verbose = verbose
                    self.n = 0
                    self.A, self.b = A, b

                def __call__(self, x: NDArray):
                    if self.n % self.verbose == 0:
                        xp = pycu.get_array_module(x)
                        print(f"Relative residual norm:{xp.linalg.norm(self.b - self.A(x)) / xp.linalg.norm(self.b)}")

            kwargs.update(dict(callback=CallBack(verbose, A, b)))

        xp = pycu.get_array_module(arr)
        if xp is np:
            spx = splin
        elif pycu.deps.CUPY_ENABLED and (xp is cp):
            import cupyx.scipy.sparse.linalg as spx
        else:
            raise NotImplementedError
        return spx.cg(A, b, **kwargs)[0]

    def dagger(self, damp: typ.Optional[float] = None, **kwargs) -> "LinOp":
        dagger = LinOp(self.shape[::-1])
        dagger.apply = types.MethodType(lambda obj, x: self.pinv(x, damp, **kwargs), dagger)
        dagger.adjoint = types.MethodType(lambda obj, x: self.T.pinv(x, damp, **kwargs), dagger)
        return dagger


class LinFunc(DiffFunc, LinOp):
    def __init__(self, shape: typ.Union[typ.Union[int, None], typ.Tuple[int, typ.Union[int, None]]]):
        DiffFunc.__init__(self, shape)
        LinOp.__init__(self, shape)

    def __add__(
        self: "LinFunc", other: typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]
    ) -> typ.Union["Map", "DiffMap", "Func", "DiffFunc", "ProxFunc", "LinOp", "LinFunc"]:
        return ProxFunc.__add__(other, self)


class SquareOp(LinOp):
    def __init__(self, shape: typ.Union[int, typ.Tuple[int, ...]]):
        shape = tuple(shape)
        if len(shape) > 1 and (shape[0] != shape[1]):
            raise ValueError(f"Inconsistent shape {shape} for operator of type {SquareOp}")
        super(SquareOp, self).__init__(shape=(shape[0], shape[0]))


class NormalOp(SquareOp):
    @pycrt.enforce_precision(o=True)
    def eigvals(self, k: int, which="LM", gpu: bool = False, **kwargs) -> NDArray:
        kwargs.update(dict(k=k, which=which, return_eigenvectors=False))
        if pycu.deps.CUPY_ENABLED and gpu:
            import cupyx.scipy.sparse.linalg as spx
        else:
            spx = splin
        return spx.eigs(self.to_scipy_operator(pycrt.getPrecision().value, gpu=gpu), **kwargs)

    def cogram(self) -> "NormalOp":
        return self.gram().specialize(cast_to=SelfAdjointOp)


class SelfAdjointOp(NormalOp):
    def adjoint(self, arr: NDArray) -> NDArray:
        return self.apply(arr)

    @property
    def T(self) -> "SelfAdjointOp":
        return self

    @pycrt.enforce_precision(o=True)
    def eigvals(self, k: int, which="LM", gpu: bool = False, **kwargs) -> NDArray:
        kwargs.update(dict(k=k, which=which, return_eigenvectors=False))
        if pycu.deps.CUPY_ENABLED and gpu:
            import cupyx.scipy.sparse.linalg as spx
        else:
            spx = splin
        return spx.eigsh(self.to_scipy_operator(pycrt.getPrecision().value, gpu=gpu), **kwargs)


class UnitOp(NormalOp):
    def __init__(self, shape: typ.Union[int, typ.Tuple[int, ...]]):
        super(UnitOp, self).__init__(shape)
        self._lipschitz = 1

    def lipschitz(self, **kwargs) -> float:
        return self._lipschitz

    def pinv(self, arr: NDArray, **kwargs) -> NDArray:
        return self.adjoint(arr)

    def dagger(self, **kwargs) -> "UnitOp":
        return self.T


class ProjOp(SquareOp):
    def __pow__(self, power: int) -> typ.Union["ProjOp", "UnitOp"]:
        if power == 0:
            from pycsou.linop.base import IdentityOperator

            return IdentityOperator(self.shape)
        else:
            return self


class OrthProjOp(ProjOp, SelfAdjointOp):
    def __init__(self, shape: typ.Union[int, typ.Tuple[int, ...]]):
        super(OrthProjOp, self).__init__(shape)
        self._lipschitz = 1

    def lipschitz(self, **kwargs) -> float:
        return self._lipschitz

    def pinv(self, arr: NDArray, **kwargs) -> NDArray:
        return self.apply(arr)

    def dagger(self, **kwargs) -> "OrthProjOp":
        return self


class PosDefOp(SelfAdjointOp):
    pass


_base_operators = frozenset([Map, DiffMap, Func, DiffFunc, ProxFunc, LinOp, LinFunc])
