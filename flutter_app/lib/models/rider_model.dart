class Rider {
  final String id;
  final String token;
  final String name;
  final String phone;
  final String? email;
  final double? rating;

  Rider({
    required this.id,
    required this.token,
    required this.name,
    required this.phone,
    this.email,
    this.rating,
  });

  factory Rider.fromJson(Map<String, dynamic> json) {
    final id = (json['id'] ?? json['_id'] ?? json['rider_id'] ?? '').toString();
    final token = (json['token'] ?? '').toString();
    if (id.isEmpty || token.isEmpty) {
      throw ArgumentError('Invalid rider auth payload');
    }

    return Rider(
      id: id,
      token: token,
      name: (json['name'] ?? 'Rider').toString(),
      phone: (json['phone'] ?? '').toString(),
      email: json['email'],
      rating: json['rating']?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'token': token,
        'name': name,
        'phone': phone,
        'email': email,
        'rating': rating,
      };
}
