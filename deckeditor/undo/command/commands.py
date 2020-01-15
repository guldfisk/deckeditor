from PyQt5.QtWidgets import QUndoCommand

from magiccube.collections.delta import CubeDeltaOperation


# class ModifyCubeModel(QUndoCommand):
#
#     def __init__(self, cube_model: CubeModel, cube_delta_operation: CubeDeltaOperation):
#         super().__init__(
#             self._stringify_cube_delta_operation(
#                 cube_delta_operation
#             )
#         )
#         self._cube_model = cube_model
#         self._cube_delta_operation = cube_delta_operation
#
#     @classmethod
#     def _stringify_cube_delta_operation(cls, cube_delta_operation: CubeDeltaOperation) -> str:
#         if len(cube_delta_operation.cubeables.distinct_elements()) <= 2:
#             return ', '.join(
#                 ('+' if multiplicity > 0 else '') + str(multiplicity) + ' ' + str(cubeable)
#                 for cubeable, multiplicity in
#                     cube_delta_operation.cubeables.items()
#             )
#         else:
#             return 'mod cube'
#
#     def redo(self) -> None:
#         self._cube_model.modify(
#             self._cube_delta_operation
#         )
#
#     def undo(self) -> None:
#         self._cube_model.modify(
#             ~self._cube_delta_operation
#         )
#
#
# class InterTransferCubeModels(QUndoCommand):
#
#     def __init__(self, giver: CubeModel, receiver: CubeModel, cube_delta_operation: CubeDeltaOperation):
#         super().__init__('cube transfer')
#         self._giver = giver
#         self._receiver = receiver
#         self._cube_delta_operation = cube_delta_operation
#
#     def redo(self) -> None:
#         self._giver.modify(
#             ~self._cube_delta_operation
#         )
#         self._receiver.modify(
#             self._cube_delta_operation
#         )
#
#     def undo(self) -> None:
#         self._giver.modify(
#             self._cube_delta_operation
#         )
#         self._receiver.modify(
#             ~self._cube_delta_operation
#         )
