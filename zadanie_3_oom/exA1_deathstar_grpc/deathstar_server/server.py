import grpc
import sys
from concurrent import futures
import deathstar_pb2
import deathstar_pb2_grpc

class DeathStarManagementServicer(deathstar_pb2_grpc.DeathStarManagementServicer):
    def __init__(self, sector_name, prefix):
        self.sector_name = sector_name
        self.devices = [
            deathstar_pb2.DeviceInfo(id=f"{prefix}-LASER-MAIN", name="Planetary Laser", sector=sector_name, type=deathstar_pb2.WEAPON_PLANET_LASER, status=deathstar_pb2.OPERATIONAL),
            deathstar_pb2.DeviceInfo(id=f"{prefix}-LASER-DEF", name="Defensive Laser Battery", sector=sector_name, type=deathstar_pb2.WEAPON_DEFENSIVE_LASERS, status=deathstar_pb2.OPERATIONAL),
            deathstar_pb2.DeviceInfo(id=f"{prefix}-DOOR-H", name="Hangar Blast Doors", sector=sector_name, type=deathstar_pb2.HANGAR_BLAST_DOOR, status=deathstar_pb2.OPERATIONAL),
            deathstar_pb2.DeviceInfo(id=f"{prefix}-SCAN-LIFE", name="Bio-Signal Scanner", sector=sector_name, type=deathstar_pb2.LIFE_FORM_SCANNER, status=deathstar_pb2.OPERATIONAL),
            deathstar_pb2.DeviceInfo(id=f"{prefix}-SCAN-DEV", name="Space Scanner", sector=sector_name, type=deathstar_pb2.DEVICE_SCANNER, status=deathstar_pb2.MAINTENANCE)
        ]

    def ListDevices(self, request, context):
        print(f"[{self.sector_name}] Reporting device status.")
        return deathstar_pb2.DeviceList(devices=self.devices)

    def ChangeDeviceState(self, request, context):
        print(f"[{self.sector_name}] Order received for {request.device_id}")
        action = request.WhichOneof('action')
        
        if action == 'door_action':
            status = deathstar_pb2.DoorAction.Name(request.door_action)
            return deathstar_pb2.ActionResponse(success=True, message=f"Door {request.device_id}: Status changed to {status}")
        
        elif action == 'weapon_command':
            cmd = request.weapon_command.WhichOneof('command')
            if cmd == 'planet_laser_power_percent':
                p = request.weapon_command.planet_laser_power_percent
                if p > 100: return deathstar_pb2.ActionResponse(success=False, message="REACTOR OVERLOAD!", error_code=500)
                return deathstar_pb2.ActionResponse(success=True, message=f"Planetary laser power set to {p}%")
            else:
                c = request.weapon_command.fire_defensive_lasers
                return deathstar_pb2.ActionResponse(success=True, message=f"Covering fire at coordinates X:{c.x} Y:{c.y}")

        return deathstar_pb2.ActionResponse(success=False, message="Invalid order")

    def RunScanner(self, request, context):
        print(f"[{self.sector_name}] Scanning sector {request.target_sector} with {request.scanner_id}")
        if "LIFE" in request.scanner_id:
            res = deathstar_pb2.ScanResult(life_form=deathstar_pb2.LifeFormDetails(species="Rebels", count=42, is_hostile=True))
        else:
            res = deathstar_pb2.ScanResult(ship_or_device=deathstar_pb2.ScannedDeviceDetails(object_class="Millennium Falcon", shields_active=True))
        return deathstar_pb2.ScanResponse(detected_objects=[res])

def serve():
    port = sys.argv[1] if len(sys.argv) > 1 else '50051'
    name = sys.argv[2] if len(sys.argv) > 2 else 'SECTOR ALPHA'
    prefix = sys.argv[3] if len(sys.argv) > 3 else 'ALPHA'
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    deathstar_pb2_grpc.add_DeathStarManagementServicer_to_server(DeathStarManagementServicer(name, prefix), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Server {name} started on port {port}")
    server.wait_for_termination()

if __name__ == '__main__': 
    serve()