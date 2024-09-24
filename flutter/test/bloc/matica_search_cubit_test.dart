import 'package:flutter_test/flutter_test.dart';
import 'package:matica/bloc/matica_search_cubit.dart';
import 'package:matica/services/matica.dart';
import 'package:mocktail/mocktail.dart';

class MockMaticaDictionary extends Mock implements MaticaDictionary{}

void main(){
  late MaticaSearchCubit qubit;
  late MockMaticaDictionary dictionary;

  setUp(() {
    dictionary = MockMaticaDictionary();
    qubit = MaticaSearchCubit(dictionary: dictionary);
  });

  tearDown((){
    reset(dictionary);
    qubit.close();
  });

  test('searchHeadword emits MaticaLoading and MaticaLoaded', () async {
    // Arrange
    final mockResults = <MaticaEntry>[];

    when(() => dictionary.getEntriesByHeadwordPattern(any()))
        .thenAnswer((_) async => mockResults);

    final future = expectLater(qubit.stream, emitsInOrder([
      isA<MaticaLoading>(),
      isA<MaticaLoaded>()
    ]));

    // Act
    qubit.searchHeadword('pattern');
    print("start listen");
    // Assert
    await future;
  });

}

