import 'package:flutter_test/flutter_test.dart';

import 'package:ridershield_ai/main.dart';

void main() {
  testWidgets('App bootstraps', (WidgetTester tester) async {
    await tester.pumpWidget(const RiderShieldApp());
    expect(find.byType(RiderShieldApp), findsOneWidget);
  });
}
