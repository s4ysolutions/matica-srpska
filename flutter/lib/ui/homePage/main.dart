import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:matica/bloc/matica_search_cubit.dart';
import 'package:matica/services/matica.dart';
import 'package:matica/ui/homePage/searchResults.dart';

import 'SearchField.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key, required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        body: BlocProvider(
            create: (context) =>
                MaticaSearchCubit(dictionary: MaticaDictionary()),
            child: Padding(
                padding: const EdgeInsets.all(8),
                child: Column(children: [
                  const SearchField(),
                  SearchResults(),
                ]))));
  }
}
