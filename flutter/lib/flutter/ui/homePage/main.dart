import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:logger/logger.dart';
import 'package:matica/flutter/ui/homePage/search_results.dart';
import 'package:matica/services/matica.dart';
import 'package:provider/provider.dart';

import 'search_field.dart';

class HomePage extends StatelessWidget {
  final String title;

  const HomePage({super.key, required this.title});

  @override
  Widget build(BuildContext context) {
    Provider.of<Logger>(context).d("HomePage build");
    return Scaffold(
        body: MultiProvider(
            providers: [
          StreamProvider<MaticaSearchResults>(
              create: (_) =>
                  Provider.of<MaticaService>(context).searchResultsStream,
              initialData: MaticaSearchResults.empty),
          StreamProvider<MaticaSearchState>(
              create: (_) =>
                  Provider.of<MaticaService>(context).searchStateStream,
              initialData: MaticaSearchState.uninitialized),
        ],
            child: SafeArea(
                child: Padding(
                    padding: EdgeInsets.all(8),
                    child: Column(mainAxisSize: MainAxisSize.max, children: [
                      SearchField(),
                      SizedBox(
                        height: 8,
                      ),
                      Expanded(child: SearchResultsField())
                    ])))));
  }
}
