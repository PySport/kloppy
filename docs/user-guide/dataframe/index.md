# Dataframe output

## `to_df`

Polars vs Pandas

## Selecting output columns

When you want to export a set of attributes you can specify a wildcard pattern. This pattern is matched against all default (exported by the Default Transformer) attributes.

## Adding metadata

The metadata can also be used when transforming a dataset to a pandas dataframe. Using keyword argument additional columns can be created.

## Attribute transformers

Attribute transformer make it possible to add predefined attributes to a dataset. The attributes are calculated during export to a pandas DataFrame. Kloppy does provide some Transformers like one to calculate the angle to the goal, and one to calculate the distance to the goal. When you need additional Transformers you can write your one by providing a Callable to to_df.

## User-defined transformers

Transformers are nothing more than a function which accepts a Event and returns Dict (Callable[[Event], Dict])). The Transformers provided by kloppy are actually classes that define a **call** method. You can also use a lambda function or any other function to transform attributes.

When you use named attributes (specified using a keyword argument) the returned value can be any type (Callable[[Event], Any]).
