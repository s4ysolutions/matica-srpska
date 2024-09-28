part of 'matica_bloc.dart';

sealed class MaticaEvent extends Equatable {
  const MaticaEvent();
}

final class _MaticaServiceNotReady extends MaticaEvent {
  @override
  List<Object> get props => [];
}

final class _MaticaServiceReady extends MaticaEvent {
  @override
  List<Object> get props => [];
}

final class _MaticaServiceSearching extends MaticaEvent {
  @override
  List<Object> get props => [];
}

final class _MaticaServiceProvidedResults extends MaticaEvent {
  final SearchResults results;

  const _MaticaServiceProvidedResults(this.results);

  @override
  List<Object> get props => [results];
}

final class MaticaSearchHeadwordPrefix extends MaticaEvent {
  final String prefix;

  const MaticaSearchHeadwordPrefix(this.prefix);

  @override
  List<Object> get props => [prefix];
}
