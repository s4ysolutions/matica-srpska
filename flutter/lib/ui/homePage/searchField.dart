import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:matica/bloc/matica_search_cubit.dart';

class SearchField extends StatelessWidget {
  const SearchField({super.key});

  @override
  Widget build(BuildContext context) {
    final search = context.read<MaticaSearchCubit>();
    return TextField(
      decoration: InputDecoration(
        hintText: AppLocalizations.of(context)?.searchFieldHint,
        prefixIcon: const Icon(Icons.search),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      onChanged: (value) => search.searchHeadword(value),
    );
  }
}