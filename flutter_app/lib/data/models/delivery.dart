class DeliveryModel {
  final String id;
  final String status;
  final String? address;
  final double? dropLat;
  final double? dropLng;

  const DeliveryModel({
    required this.id,
    required this.status,
    this.address,
    this.dropLat,
    this.dropLng,
  });

  factory DeliveryModel.fromJson(Map<String, dynamic> json) {
    return DeliveryModel(
      id: (json['id'] ?? json['_id'] ?? '').toString(),
      status: (json['status'] ?? 'unknown').toString(),
      address: json['address']?.toString(),
      dropLat: (json['drop_lat'] as num?)?.toDouble(),
      dropLng: (json['drop_lng'] as num?)?.toDouble(),
    );
  }
}
