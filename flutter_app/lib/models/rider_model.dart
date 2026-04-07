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
    return Rider(
      id: json['id'] ?? json['_id'],
      token: json['token'],
      name: json['name'] ?? 'Rider',
      phone: json['phone'],
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
