import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:matica/data_layer/dictionary_random.dart';
import 'package:matica/flutter/ui/homePage/search_results.dart';
import 'package:matica/services/matica.dart';

import '../../bloc/matica_bloc.dart';
import 'search_field.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key, required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    print("HomePage build");
    return Scaffold(
        body: BlocProvider(
            create: (context) {
              final service = MaticaService(DictionaryRandomProvider());
              final bloc = MaticaBloc(service);
              service.init();
              return bloc;
            },
            child: Padding(
                padding: EdgeInsets.all(8),
                child: Column(mainAxisSize: MainAxisSize.max, children: [
                  SearchField(),
                  SizedBox(
                    height: 8,
                  ),
                  Expanded(child: SearchResultsField())
                ]))));
  }
}
