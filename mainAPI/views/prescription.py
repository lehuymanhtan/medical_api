"""
Prescription (medicines) Views
Nested under /examinations/{examination_pk}/medicines/
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from mainAPI.models import Examination, Prescription
from mainAPI.serializers.examination import PrescriptionSerializer, PrescriptionCreateSerializer
from mainAPI.permissions import IsDoctor, IsDoctorOrOwnerReadOnly


@extend_schema_view(
    list=extend_schema(
        summary='Danh sách thuốc của phiên khám',
        tags=['Doctor Workflow', 'Patient Dashboard'],
        description='Lấy danh sách các loại thuốc đã được kê cho phiên khám này. Bác sĩ có thể xem tất cả, sinh viên chỉ có thể xem thuốc từ phiên khám đã hoàn tất (COMPLETED) của chính mình.'
    ),
    retrieve=extend_schema(
        summary='Chi tiết một loại thuốc đã kê',
        tags=['Doctor Workflow', 'Patient Dashboard'],
        description='Xem chi tiết thuốc. Sinh viên chỉ có thể xem nếu thuộc phiên khám đã hoàn tất (COMPLETED) của mình.'
    ),
    create=extend_schema(
        summary='Thêm thuốc vào đơn thuốc',
        tags=['Doctor Workflow'],
        description='Chỉ bác sĩ mới có quyền thêm thuốc vào đơn thuốc của phiên khám.',
        examples=[
            OpenApiExample(
                'Thêm thuốc',
                value={
                    'name': 'Paracetamol 500mg',
                    'morning': True,
                    'evening': True,
                    'before_meal': False,
                    'quantity': 10,
                    'summary': 'Uống sau khi ăn'
                },
                request_only=True,
            )
        ]
    ),
    update=extend_schema(
        summary='Cập nhật thông tin thuốc',
        tags=['Doctor Workflow']
    ),
    partial_update=extend_schema(
        summary='Cập nhật một phần thông tin thuốc',
        tags=['Doctor Workflow']
    ),
    destroy=extend_schema(
        summary='Xóa thuốc khỏi đơn thuốc',
        tags=['Doctor Workflow']
    )
)
class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    CRUD for individual prescription items under an examination.
    Doctors can read/write, students can only read their own.
    """
    permission_classes = [IsDoctorOrOwnerReadOnly]

    def get_queryset(self):
        qs = Prescription.objects.filter(
            examination_id=self.kwargs['examination_id']
        )
        if hasattr(self.request.user, 'role') and self.request.user.role == 'STUDENT':
            qs = qs.filter(
                examination__patient=self.request.user,
                examination__status=Examination.Status.COMPLETED
            )
        return qs

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PrescriptionCreateSerializer
        return PrescriptionSerializer

    def perform_create(self, serializer):
        examination = Examination.objects.get(pk=self.kwargs['examination_id'])
        serializer.save(examination=examination)
