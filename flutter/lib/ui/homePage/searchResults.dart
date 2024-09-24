import 'package:flutter/cupertino.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:matica/bloc/matica_search_cubit.dart';

class SearchResults extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return BlocBuilder<MaticaSearchCubit, MaticaState> (
      builder: (context, state){
        return switch(state) {
          MaticaLoaded() => Text(state.results.length.toString()),
          MaticaLoading() => Text("...."),
          MaticaError() => Text(state.message),
        };
      },
    );
  }
}