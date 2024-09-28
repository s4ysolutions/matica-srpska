part of 'matica_bloc.dart';

sealed class MaticaState extends Equatable {
  const MaticaState();

  List<DictionaryEntry> get results => [];
}

final class MaticaNotReady extends MaticaState {
  static final MaticaNotReady instance = MaticaNotReady._();

  @override
  List<Object> get props => [];

  const MaticaNotReady._();
}

final class MaticaReady extends MaticaState {
  static final MaticaReady instance = MaticaReady._();

  @override
  List<Object> get props => [];

  const MaticaReady._();
}

final class MaticaSearching extends MaticaState {
  static final MaticaSearching instance = MaticaSearching._();

  @override
  List<Object> get props => [];

  const MaticaSearching._();
}

final class MaticaHasResults extends MaticaState {
  @override
  List<Object> get props => [_results];

  final SearchResults _results;

  @override
  List<DictionaryEntry> get results => _results.entries;

  DictionaryFilter get filter => _results.filter;

  const MaticaHasResults(this._results);
}
