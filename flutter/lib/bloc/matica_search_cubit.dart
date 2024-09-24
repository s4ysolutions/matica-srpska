import 'package:bloc/bloc.dart';
import 'package:matica/services/matica.dart';

sealed class MaticaState {
  const MaticaState();
}

class MaticaLoaded extends MaticaState {
  final List<MaticaEntry> results;

  const MaticaLoaded({required this.results});
}

class MaticaLoading extends MaticaState {}

class MaticaError extends MaticaState {
  final String message;
  final Object? error;
  final StackTrace? stackTrace;

  const MaticaError(this.message, [this.error, this.stackTrace]);
}

const maticaInitial = MaticaLoaded(results: []);

class MaticaSearchCubit extends Cubit<MaticaState> {
  final MaticaDictionary _dictionary;

  MaticaSearchCubit({required dictionary})
      : _dictionary = dictionary,
        super(maticaInitial);

  void searchHeadword(String pattern) async {
    print("emit loading");
    emit(MaticaLoading());
    try {
      final results = await _dictionary.getEntriesByHeadwordPattern(pattern);
      print("emit loaded");
      emit(MaticaLoaded(results: results));
    } catch (e, stackTrace) {
      emit(MaticaError(e.toString(), e, stackTrace));
      onError(e, StackTrace.current);
    }
  }
}
