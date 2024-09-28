This the next layer above the data layer. It is responsible for providing
problem domain specific interface to the data layer(s).

Currently, it wraps the data layer exporting the "addFilter" function and
stream of results. 

The approach is not perfect, but still chosen to see how reactive interface
can be implemented with streams and used in the flutter application.

This layer is supposed to be used by the application or presentation layer