class Delivery {
  final String id;
  final String status;
  final String? customerName;
  final String? address;
  final double? dropLat;
  final double? dropLng;
  final String? digiPin;

  Delivery({
    required this.id,
    required this.status,
    this.customerName,
    this.address,
    this.dropLat,
    this.dropLng,
    this.digiPin,
  });

  factory Delivery.fromJson(Map<String, dynamic> json) {
    return Delivery(
      id: json['id'] ?? json['_id'],
      status: json['status'],
      customerName: json['customer_name'],
      address: json['address'],
      dropLat: (json['drop_lat'] as num?)?.toDouble(),
      dropLng: (json['drop_lng'] as num?)?.toDouble(),
      digiPin: json['digi_pin'],
    );
  }
}
