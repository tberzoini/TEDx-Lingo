import 'dart:convert';
import 'package:http/http.dart' as http;
import 'models/talk.dart';
import 'models/watch_next.dart';
import 'models/flashcard.dart';

const String _talksByTagUrl =
    'https://u1ho46t5l6.execute-api.us-east-1.amazonaws.com/default/Get_Talks_By_Tag';
const String _watchNextUrl =
    'https://vrj067f6fc.execute-api.us-east-1.amazonaws.com/default/Get_Watch_Next_by_Idx';
const String _flashcardsUrl =
    'https://0bwe248ml6.execute-api.us-east-1.amazonaws.com/default/Manage_Flashcards';

final List<Talk> _realCatalogFallback = [
  Talk(
    id: '551212',
    title: 'Can you solve the trickster god riddle?',
    details:
        'A logic puzzle talk ideal for practicing English vocabulary with TEDx Lingo.',
    mainSpeaker: 'Alex Rosenthal',
    url:
        'https://www.ted.com/talks/alex_rosenthal_can_you_solve_the_trickster_god_riddle',
    keyPhrases: ['riddle', 'trickster', 'solve', 'logic', 'technology'],
  ),
  Talk(
    id: '418096',
    title: 'Can you solve the birthday cake riddle?',
    details:
        'Ideal duration (4 min) to complete your Daily Streak with ~172 useful vocabulary words.',
    mainSpeaker: 'Marie Brodsky',
    url:
        'https://www.ted.com/talks/marie_brodsky_can_you_solve_the_birthday_cake_riddle',
    keyPhrases: ['riddle', 'solve', 'cake', 'logic', 'math'],
  ),
  Talk(
    id: '547664',
    title: "The dungeon master's riddle",
    details:
        'Ideal duration (5 min) for your Daily Streak with ~157 useful vocabulary words.',
    mainSpeaker: 'Alex Rosenthal',
    url: 'https://www.ted.com/talks/alex_rosenthal_the_dungeon_master_s_riddle',
    keyPhrases: ['riddle', 'dungeon', 'rosenthal', 'games', 'logic'],
  ),
];

Future<List<Talk>> initEmptyList() async {
  return [];
}

Future<List<Talk>> getTalksByTag(String tag, int page) async {
  try {
    final url = Uri.parse(_talksByTagUrl);
    final response = await http
        .post(
          url,
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({
            'tag': tag,
            'page': page,
            'doc_per_page': 6,
          }),
        )
        .timeout(const Duration(seconds: 4));

    if (response.statusCode == 200) {
      final body = utf8.decode(response.bodyBytes);
      final List<dynamic> jsonList = json.decode(body);
      if (jsonList.isNotEmpty) {
        return jsonList.map((json) => Talk.fromJSON(json)).toList();
      }
    }
  } catch (_) {
    // Fallback to curated catalog if external tag endpoint is unreachable
  }

  final q = tag.toLowerCase();
  final filtered = _realCatalogFallback.where((t) {
    return t.title.toLowerCase().contains(q) ||
        t.mainSpeaker.toLowerCase().contains(q) ||
        t.keyPhrases.any((k) => k.toLowerCase().contains(q));
  }).toList();

  return filtered.isNotEmpty ? filtered : _realCatalogFallback;
}

Future<WatchNextResponse> getWatchNextById(String talkId) async {
  final postResponse = await http.post(
    Uri.parse(_watchNextUrl),
    headers: const {'Content-Type': 'application/json'},
    body: jsonEncode({
      'id': talkId,
      '_id': talkId,
      'idx': talkId,
    }),
  );

  if (postResponse.statusCode == 200) {
    final body = utf8.decode(postResponse.bodyBytes);
    return WatchNextResponse.fromJSON(json.decode(body));
  }

  final getUrl = Uri.parse('$_watchNextUrl?id=$talkId');
  final getResponse = await http.get(
    getUrl,
    headers: const {'Content-Type': 'application/json'},
  );

  if (getResponse.statusCode == 200) {
    final body = utf8.decode(getResponse.bodyBytes);
    return WatchNextResponse.fromJSON(json.decode(body));
  }

  throw Exception(
    'Error ${postResponse.statusCode}: ${utf8.decode(postResponse.bodyBytes)}',
  );
}

Future<List<Flashcard>> getUserFlashcards(String userId) async {
  final url = Uri.parse('$_flashcardsUrl?user_id=$userId');
  final response = await http.get(
    url,
    headers: const {'Content-Type': 'application/json'},
  );

  if (response.statusCode == 200) {
    final body = utf8.decode(response.bodyBytes);
    final Map<String, dynamic> jsonMap = json.decode(body);
    final List<dynamic> list = jsonMap['flashcards'] ?? [];
    return list
        .map((item) => Flashcard.fromJSON(item as Map<String, dynamic>))
        .toList();
  } else {
    throw Exception('Failed to load Flashcards (${response.statusCode})');
  }
}

Future<Flashcard> saveFlashcard(Flashcard card) async {
  final url = Uri.parse(_flashcardsUrl);
  final response = await http.post(
    url,
    headers: const {'Content-Type': 'application/json'},
    body: jsonEncode(card.toJSON()),
  );

  if (response.statusCode == 200 || response.statusCode == 201) {
    final body = utf8.decode(response.bodyBytes);
    final Map<String, dynamic> jsonMap = json.decode(body);
    return Flashcard.fromJSON(jsonMap['flashcard'] ?? card.toJSON());
  } else {
    throw Exception('Failed to save Flashcard (${response.statusCode})');
  }
}
