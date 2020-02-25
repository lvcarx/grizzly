from grizzly.expression import Eq, Ne, Ge, Gt, Le, Lt, And, Or, Expr, ColRef, ExpressionException
from grizzly.generator import GrizzlyGenerator
from grizzly.aggregates import AggregateType
###########################################################################
# Base DataFrame with common operations

class DataFrame(object):

  tVarCounter = 0

  @staticmethod
  def _incrAndGetTupleVar():
    tVar = f"_t{DataFrame.tVarCounter}"
    DataFrame.tVarCounter += 1
    return tVar

  def __init__(self, columns, parents, alias):
    super(DataFrame, self).__init__()

    self.alias = alias
    self.columns = columns

    if parents is None or type(parents) is list:
      self.parents = parents
    else:
      self.parents = [parents]

  def hasColumn(self, colName):
    if not self.columns:
      return True

    for ref in self.columns:
      if ref.column == colName:
        return True

    return False

  def setAlias(self, newAlias):
    if self.columns:
      for c in self.columns:
        c.df.alias = newAlias

    self.alias = newAlias

  def filter(self, expr):
    return Filter(expr, self)

  def project(self, cols):
    return Projection(cols, self)

  def distinct(self):
    return Projection(None, self, doDistinct = True)

  def join(self, other, on, how="inner", comp = "="):

    if isinstance(on, list):
      
      from grizzly.expression import ExpressionException
      if not self.hasColumn(on[0]):
        raise ExpressionException(f"No such column {on[0]} for join in left hand side")
      if not other.hasColumn(on[1]):
        raise ExpressionException(f"No such column {on[1]} for join in right hand side")

    return Join(self, other, on, how, comp)

  def groupby(self, groupCols):
    return Grouping(groupCols, self)

  ###################################
  # shortcuts

  def __getattr__(self, name):
    return self.project([ColRef(name, self)])

  def __getitem__(self, key):
    theType = type(key)

    if isinstance(key, Expr):
      # print(f"filter col: {key}")
      return self.filter(key)
    elif theType is str:
      # print(f"projection col: {key}")
      return self.project([ColRef(key, self)])
    elif theType is Projection:
      return self.project([key.attrs[0]])
    elif theType is list:
      
      projList = []
      for e in key:
        t = type(e)
        if t is str:
          projList.append(ColRef(e, self))
        elif t is Projection:
          projList.append(e.attrs[0])
        else:
          raise ExpressionException(f"expected a column name string or projection, but got {e}")

      return self.project(projList)
    else:
      print(f"{key} has type {theType} -- ignoring")
      return self

  ###################################
  # Comparison expressions

  def __eq__(self, other):
    if not isinstance(self, Projection) or len(self.attrs) != 1:
      raise ExpressionException("Must have a projection with exactly one attribute")

    if isinstance(other, DataFrame):
      r = other.attrs[0]
    else:
      r = other

    expr = Eq(self.attrs[0], r)
    return expr

  def __gt__(self, other):
    if not isinstance(self, Projection) or len(self.attrs) != 1:
      raise ExpressionException("Must have a projection with exactly one attribute")

    if isinstance(other, DataFrame):
      r = other.attrs[0]
    else:
      r = other

    expr = Gt(self.attrs[0], r)
    return expr

  def __lt__(self, other):
    if not isinstance(self, Projection) or len(self.attrs) != 1:
      raise ExpressionException("Must have a projection with exactly one attribute")

    if isinstance(other, DataFrame):
      r = other.attrs[0]
    else:
      r = other

    expr = Lt(self.attrs[0], r)
    return expr

  def __ge__(self, other):
    if not isinstance(self, Projection) or len(self.attrs) != 1:
      raise ExpressionException("Must have a projection with exactly one attribute")

    if isinstance(other, DataFrame):
      r = other.attrs[0]
    else:
      r = other

    expr = Ge(self.attrs[0], r)
    return expr
  
  def __le__(self, other):
    if not isinstance(self, Projection) or len(self.attrs) != 1:
      raise ExpressionException("Must have a projection with exactly one attribute")

    if isinstance(other, DataFrame):
      r = other.attrs[0]
    else:
      r = other

    expr = Le(self.attrs[0], r)
    return expr

  def __ne__(self, other):
    if not isinstance(self, Projection) or len(self.attrs) != 1:
      raise ExpressionException("Must have a projection with exactly one attribute")

    if isinstance(other, DataFrame):
      r = other.attrs[0]
    else:
      r = other

    expr = Ne(self.attrs[0], r)
    return expr

  ###########################################################################
  # Actions
  ###########################################################################


  ###################################
  # aggregation functions
  
  def min(self, col=None):
    # return self._execAgg("min",col)
    return GrizzlyGenerator.aggregate(self, col, AggregateType.MIN)

  def max(self, col=None):
    # return self._execAgg("max",col)
    return GrizzlyGenerator.aggregate(self, col, AggregateType.MAX)

  def mean(self, col=None):
    # return self._execAgg('avg',col)
    return GrizzlyGenerator.aggregate(self, col, AggregateType.MEAN)

  def count(self, col=None):
    colName = "*"
    if col is not None:
      colName = col
    # return self._execAgg("count",colName)
    return GrizzlyGenerator.aggregate(self, colName, AggregateType.COUNT)

  def sum(self , col):
    return GrizzlyGenerator.aggregate(self, col, AggregateType.SUM)
    # return self._execAgg("sum", col)

  ###################################
  # show functions

  def generate(self):
    return GrizzlyGenerator.generate(self)

  def show(self, pretty=False, delim=",", maxColWidth=20):
    GrizzlyGenerator.execute(self,delim,pretty,maxColWidth)
    
  def __str__(self):
    return GrizzlyGenerator.toString(self)
    
###########################################################################
# Concrete DataFrames representing an operation


class Table(DataFrame):
  def __init__(self, table):
    self.table = table
    super().__init__([], None, DataFrame._incrAndGetTupleVar())

class Projection(DataFrame):

  def __init__(self, attrs, parent, doDistinct = False):
    if attrs and not isinstance(attrs[0], ColRef):
      self.attrs = [ColRef(attr, parent) for attr in attrs]
    else:
      self.attrs = attrs

    self.doDistinct = doDistinct
    super().__init__(self.attrs, parent, parent.alias)

class Filter(DataFrame):

  def __init__(self, expr, parent):
    super().__init__(parent.columns, parent, parent.alias)
    self.expr = expr
 

class Grouping(DataFrame):

  def __init__(self, groupCols, parent):
    if not isinstance(groupCols[0], ColRef):
      self.groupCols = [ColRef(col, parent) for col in groupCols]
    else:
      self.groupCols = groupCols

    super().__init__(self.groupCols, parent, parent.alias)

class Join(DataFrame):
  def __init__(self, parent, other, on, how, comp):
    super().__init__(parent.columns.extend(other.columns), parent, parent.alias)
    self.right = other
    self.on = on
    self.how = how
    self.comp = comp