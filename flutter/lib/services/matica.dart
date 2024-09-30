import 'dart:async';

import 'package:equatable/equatable.dart';
import 'package:logger/logger.dart';
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

class MaticaSearchResults extends Equatable {
  static const MaticaSearchResults empty =
      MaticaSearchResults(DictionaryNoFilter.instance, []);
  final DictionaryFilter filter;
  final List<DictionaryEntry> entries;

  const MaticaSearchResults(this.filter, this.entries);

  @override
  List<Object?> get props => [filter, entries];
}

enum MaticaSearchState {
  uninitialized,
  idle,
  searching,
  error,
}

// This service is intentionally overcomplicated
// with stream-based API to experiment with
// streams
class MaticaService {
  final DictionaryProvider _dictionary;
  final Logger _logger;
  final StreamController<MaticaSearchResults> _searchResultsController =
      StreamController<MaticaSearchResults>.broadcast();
  final StreamController<MaticaSearchState> _searchStateController =
      BehaviorSubject<MaticaSearchState>.seeded(
          MaticaSearchState.uninitialized);

  // it is not conventional API to provide search results as a stream
  // they are here just for fun
  Stream<MaticaSearchResults> get searchResultsStream =>
      _searchResultsController.stream;
  MaticaSearchResults _searchResults = MaticaSearchResults.empty;

  MaticaSearchResults get searchResults => _searchResults;

  void _setSearchResults(MaticaSearchResults newResults) {
    _searchResults = newResults;
    _searchResultsController.add(newResults);
  }

  Stream<MaticaSearchState> get searchStateStream =>
      _searchStateController.stream;
  MaticaSearchState _searchState = MaticaSearchState.uninitialized;

  MaticaSearchState get searchState => _searchState;

  void _setSearchState(MaticaSearchState newState) {
    _searchState = newState;
    _searchStateController.add(newState);
  }

  MaticaService(this._dictionary, this._logger) {}

  /*,
      {Function(Object exception, StackTrace stack)? errorHandler})
      : _errorHandler = errorHandler;*/

  Future<MaticaSearchResults> setFilter(DictionaryFilter filter) async {
    if (searchState != MaticaSearchState.idle) {
      return Future.error(
          Exception('Cannot set filter while not in idle state'));
    }
    _setSearchState(MaticaSearchState.searching);

    try {
      List<DictionaryEntry> entries = await switch (filter) {
        DictionaryPrefixFilter(pattern: final pattern) =>
            _dictionary.getEntriesByHeadwordBegin(_lat2cyr(pattern)),
        DictionaryNoFilter() => Future.value(List<DictionaryEntry>.empty()),
      };

      final results = MaticaSearchResults(filter, entries);
      _setSearchResults(results);
      _setSearchState(MaticaSearchState.idle);
      return results;
    } finally {
      // it is not wise to disable search forever, so i will just log the error
      _setSearchState(MaticaSearchState.idle);
    }
      /*
    } catch (e, s) {
      // it is not wise to disable search forever, so i will just log the error
      _setSearchState(MaticaSearchState.error);
      rethrow;
    }*/
  }

  Future<void> destroy() async {
    await _dictionary.destroy();
    _searchResultsController.close();
    _searchStateController.close();
  }

  Future<void> init() async {
    try {
      await _dictionary.init();
      _setSearchState(MaticaSearchState.idle);
    } catch (e, s) {
      _setSearchState(MaticaSearchState.error);
      rethrow;
    }
  }

  static const Map<String, String> _latinToCyrillic = {
    'A': 'А', 'B': 'Б', 'C': 'Ц', 'Č': 'Ч', 'Ć': 'Ћ', 'D': 'Д', 'Dž': 'Џ', 'Đ': 'Ђ',
    'E': 'Е', 'F': 'Ф', 'G': 'Г', 'H': 'Х', 'I': 'И', 'J': 'Ј', 'K': 'К', 'L': 'Л',
    'Lj': 'Љ', 'M': 'М', 'N': 'Н', 'Nj': 'Њ', 'O': 'О', 'P': 'П', 'R': 'Р', 'S': 'С',
    'Š': 'Ш', 'T': 'Т', 'U': 'У', 'V': 'В', 'Z': 'З', 'Ž': 'Ж',
    'a': 'а', 'b': 'б', 'c': 'ц', 'č': 'ч', 'ć': 'ћ', 'd': 'д', 'dž': 'џ', 'đ': 'ђ',
    'e': 'е', 'f': 'ф', 'g': 'г', 'h': 'х', 'i': 'и', 'j': 'ј', 'k': 'к', 'l': 'л',
    'lj': 'љ', 'm': 'м', 'n': 'н', 'nj': 'њ', 'o': 'о', 'p': 'п', 'r': 'р', 's': 'с',
    'š': 'ш', 't': 'т', 'u': 'у', 'v': 'в', 'z': 'з', 'ž': 'ж'
  };
  static String _lat2cyr(String mixed) {
    final buffer = StringBuffer();
    for (int i = 0; i < mixed.length; i++) {
      final char = mixed[i];
      final nextChar = i + 1 < mixed.length ? mixed[i + 1] : '';
      final doubleChar = char + nextChar;

      if (_latinToCyrillic.containsKey(doubleChar)) {
        buffer.write(_latinToCyrillic[doubleChar]);
        i++; // Skip the next character
      } else if (_latinToCyrillic.containsKey(char)) {
        buffer.write(_latinToCyrillic[char]);
      } else {
        buffer.write(char);
      }
    }
    return buffer.toString();
  }
}
