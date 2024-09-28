import 'dart:async';

import 'package:equatable/equatable.dart';
import 'package:matica/data_layer/dictionary.dart';
import 'package:rxdart/rxdart.dart';

sealed class DictionaryFilter extends Equatable {
  final String pattern;

  @override
  List<Object> get props => [pattern];

  const DictionaryFilter(this.pattern);
}

class DictionaryNoFilter extends DictionaryFilter {
  static const DictionaryNoFilter instance = DictionaryNoFilter._();

  const DictionaryNoFilter._() : super('');
}

class DictionaryPrefixFilter extends DictionaryFilter {
  const DictionaryPrefixFilter(super.pattern);
}

class SearchResults extends Equatable {
  static const SearchResults empty =
      SearchResults(DictionaryNoFilter.instance, []);
  final DictionaryFilter filter;
  final List<DictionaryEntry> entries;

  const SearchResults(this.filter, this.entries);
  @override
  List<Object?> get props => [filter, entries];
}

enum MaticaSearchState {
  uninitialized,
  idle,
  searching,
}

// This service is intentionally overcomplicated
// with stream-based API to experiment with
// streams
class MaticaService {
  final DictionaryProvider _dictionary;
  final StreamController<SearchResults> _searchResultsController =
      StreamController<SearchResults>.broadcast();
  final StreamController<MaticaSearchState> _searchStateController =
      BehaviorSubject<MaticaSearchState>.seeded(
          MaticaSearchState.uninitialized);

  // it is not conventional API to provide search results as a stream
  // they are here just for fun
  Stream<SearchResults> get searchResultsStream =>
      _searchResultsController.stream;

  Stream<MaticaSearchState> get searchStateStream =>
      _searchStateController.stream;

  // MaticaSearchState get searchState => _searchStateController.value;

  MaticaService(this._dictionary);

  void addFilter(DictionaryFilter filter) {
    _searchStateController.add(MaticaSearchState.searching);
    final Future<List<DictionaryEntry>> resultsFuture = switch (filter) {
      DictionaryPrefixFilter(pattern: final pattern) =>
        _dictionary.getEntriesByHeadwordBegin(pattern),
      DictionaryNoFilter() => Future.value(List<DictionaryEntry>.empty()),
    };
    resultsFuture.then((results) {
      _searchResultsController.add(SearchResults(filter, results));
      _searchStateController.add(MaticaSearchState.idle);
    });
  }

  Future<void> destroy() async {
    await _dictionary.destroy();
    _searchResultsController.close();
    _searchStateController.close();
  }

  Future<void> init() async {
    await _dictionary.init();
    _searchStateController.add(MaticaSearchState.idle);
  }
}
