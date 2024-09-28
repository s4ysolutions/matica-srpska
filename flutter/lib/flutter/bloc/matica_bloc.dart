import 'dart:async';

import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../data_layer/dictionary.dart';
import '../../services/matica.dart';

part 'matica_event.dart';

part 'matica_state.dart';

// This BLoC is intentionally overcomplicated to demonstrate how to use
// streams

class MaticaBloc extends Bloc<MaticaEvent, MaticaState> {
  late final StreamSubscription<SearchResults> _searchResultsStreamSubscription;
  late final StreamSubscription<MaticaSearchState>
      _searchStateStreamSubscription;
  final MaticaService _maticaService;

  MaticaBloc(this._maticaService) : super(MaticaNotReady.instance) {
    _searchResultsStreamSubscription =
        _maticaService.searchResultsStream.listen((data) {
      print("MaticaBloc: _searchResultsStreamSubscription.listen: data=${data.entries.length}");
      add(_MaticaServiceProvidedResults(data));
    });

    _searchStateStreamSubscription =
        _maticaService.searchStateStream.listen((state) {
      switch (state) {
        case MaticaSearchState.uninitialized:
          add(_MaticaServiceNotReady());
        case MaticaSearchState.idle:
          add(_MaticaServiceReady());
        case MaticaSearchState.searching:
          add(_MaticaServiceSearching());
      }
    });

    on<MaticaEvent>((event, emit) {
      switch (event) {
        case MaticaSearchHeadwordPrefix():
          _maticaService.addFilter(DictionaryPrefixFilter(event.prefix));
        case _MaticaServiceNotReady():
          emit(MaticaNotReady.instance);
        case _MaticaServiceReady():
          print("MaticaBloc: emit MaticaReady");
          emit(MaticaReady.instance);
        case _MaticaServiceSearching():
          emit(MaticaSearching.instance);
        case _MaticaServiceProvidedResults():
          print(
              "MaticaBloc: emit MaticaHasResults event.results=${event.results.entries.length}");
          emit(MaticaHasResults(event.results));
      }
    });
  }

  @override
  Future<void> close() {
    _searchResultsStreamSubscription.cancel();
    _searchStateStreamSubscription.cancel();
    return super.close();
  }
}
