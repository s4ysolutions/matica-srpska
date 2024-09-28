import 'package:flutter_test/flutter_test.dart';
import 'package:matica/data_layer/dictionary.dart';
import 'package:matica/flutter/bloc/matica_bloc.dart';
import 'package:matica/services/matica.dart';
import 'package:mocktail/mocktail.dart';

class MockDictionaryProvider extends Mock implements DictionaryProvider {}

// This test is integration test for MaticaBloc and MaticaService
// in order to test the private events the MaticaBloc receives from MaticaService
void main() {
  late MockDictionaryProvider mockDictionary;
  late MaticaService maticaService;

  setUp(() {
    mockDictionary = MockDictionaryProvider();
    when(() => mockDictionary.init()).thenAnswer((_) async => Future.value());
    when(() => mockDictionary.destroy())
        .thenAnswer((_) async => Future.value());
    maticaService = MaticaService(mockDictionary);
  });

  tearDown(() async {
    await maticaService.destroy();
    reset(mockDictionary);
  });

  test('MaticaBlock should be in NotReady state when created', () {
    // Arrange
    final bloc = MaticaBloc(maticaService);
    // Assert
    expect(bloc.state, MaticaNotReady.instance);
  });

  test('MaticaBlock should emit Ready state when initialized', () async {
    // Arrange
    final bloc = MaticaBloc(maticaService);
    // Assert 1
    final f1 = expectLater(bloc.stream,
            emitsInOrder([isA<MaticaNotReady>(), isA<MaticaReady>()]))
        .timeout(Duration(milliseconds: 500));
    // Act
    await maticaService.init();
    await f1;
    // Assert 2
    expect(bloc.state, MaticaReady.instance);
  });

  test('MaticaBlock should emit Searching state when searching', () async {
    // Arrange
    final DictionaryEntry testEntry =
        DictionaryEntry(headword: "headword", definition: "description");
    when(() => mockDictionary.getEntriesByHeadwordBegin('pattern'))
        .thenAnswer((_) async => Future.value([testEntry]));
    final bloc = MaticaBloc(maticaService);
    // Assert
    final f1 = expectLater(
        bloc.stream,
        emitsInOrder([
          isA<MaticaNotReady>(),
          isA<MaticaReady>(),
          isA<MaticaSearching>(),
          isA<MaticaHasResults>(),
          isA<MaticaReady>(),
        ])).timeout(Duration(milliseconds: 500));
    // Act
    await maticaService.init();
    bloc.add(MaticaSearchHeadwordPrefix('pattern'));
    await f1;
    // Assert
    expect(bloc.state, MaticaReady.instance);
  });

  test(
      "MaticaBloc should emit MaticaHasResults when MaticaService emits SearchResults",
      () async {
    // Arrange
    final DictionaryEntry testEntry =
        DictionaryEntry(headword: "headword", definition: "description");
    when(() => mockDictionary.getEntriesByHeadwordBegin('pattern'))
        .thenAnswer((_) async => Future.value([testEntry]));
    final bloc = MaticaBloc(maticaService);
    // Assert
    final f1 = expectLater(bloc.stream, emitsThrough(
      predicate<MaticaHasResults>((state) {
        return state.results.length == 1 && state.results[0] == testEntry;
      }),
    )).timeout(Duration(milliseconds: 500));
    // Act
    await maticaService.init();
    bloc.add(MaticaSearchHeadwordPrefix('pattern'));
    await f1;
    // Assert
    expect(bloc.state, MaticaReady.instance);
  });
}
