import 'package:flutter_test/flutter_test.dart';
import 'package:matica/data_layer/dictionary.dart';
import 'package:matica/services/matica.dart';
import 'package:mocktail/mocktail.dart';

class MockDictionaryProvider extends Mock implements DictionaryProvider {}

void main() {
  late MockDictionaryProvider dictionary;

  setUp(() {
    dictionary = MockDictionaryProvider();
    when(() => dictionary.init()).thenAnswer((_) async => Future.value());
  });

  tearDown(() {
    reset(dictionary);
  });
/*
  test('MaticaDictionary should be in notReadyState when created', () async {
    // Arrange & Act
    final service = MaticaService(dictionary);
    // Assert
    expect(service.searchState, MaticaSearchState.uninitialized);
  });
*/
  test('MaticaDictionary should be in idleState when created', () async {
    // Arrange
    final service = MaticaService(dictionary);
    // Assert 1
    final future = expectLater(
            service.searchStateStream,
            emitsInOrder(
                [MaticaSearchState.uninitialized, MaticaSearchState.idle]))
        .timeout(const Duration(milliseconds: 500));
    // Act
    await service.init();
    await future;
    // Assert 2
    //expect(service.searchState, MaticaSearchState.idle);
  });

  test('MaticaDictionary should be in searchingState when searching', () async {
    // Arrange
    final DictionaryEntry testEntry =
        DictionaryEntry(headword: "headword", definition: "description");
    when(() => dictionary.getEntriesByHeadwordBegin('pattern'))
        .thenAnswer((_) async => Future.value([testEntry]));
    when(() => dictionary.getEntriesByHeadwordBegin('pattern')).thenAnswer(
        (_) async => Future.value([
              DictionaryEntry(headword: "headword", definition: "description")
            ]));
    final service = MaticaService(dictionary);
    // Assert
    final future = expectLater(
        service.searchStateStream,
        emitsInOrder([
          MaticaSearchState.uninitialized,
          MaticaSearchState.idle,
          MaticaSearchState.searching,
          MaticaSearchState.idle
        ])).timeout(const Duration(milliseconds: 500));

    final futureSearchResults = expectLater(
        service.searchResultsStream,
        emits(SearchResults(DictionaryPrefixFilter("pattern"), [
          DictionaryEntry(headword: "headword", definition: "description")
        ]))).timeout(const Duration(milliseconds: 500));

    // Act
    await service.init();
    service.addFilter(DictionaryPrefixFilter("pattern"));
    await future;
    await futureSearchResults;
  });
}
