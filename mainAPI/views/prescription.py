"""
Prescription (medicines) Views
Nested under /examinations/{examination_pk}/medicines/
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from mainAPI.models import Examination, Prescription
from mainAPI.serializers.examination import PrescriptionSerializer, PrescriptionCreateSerializer
from mainAPI.permissions import IsDoctor


@extend_schema_view(
    list=extend_schema(
        summary='Danh sách thuốc của phiên khám',
        tags=['Doctor Workflow'],
        description='Lấy danh sách các loại thuốc đã được kê cho phiên khám này.'
    ),
    retrieve=extend_schema(
        summary='Chi tiết một loại thuốc đã kê',
        tags=['Doctor Workflow']
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
    Doctors only — no student write access.
    """
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Prescription.objects.filter(
            examination_id=self.kwargs['examination_id']
        )

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PrescriptionCreateSerializer
        return PrescriptionSerializer

    def perform_create(self, serializer):
        examination = Examination.objects.get(pk=self.kwargs['examination_id'])
        serializer.save(examination=examination)
