package deathstar;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import deathstar.grpc.*;
import java.util.HashMap;
import java.util.Map;
import java.util.Scanner;

public class DeathstarClientApp {

    static class DeviceLocation {
        DeviceInfo info;
        DeathStarManagementGrpc.DeathStarManagementBlockingStub stub;

        public DeviceLocation(DeviceInfo info, DeathStarManagementGrpc.DeathStarManagementBlockingStub stub) {
            this.info = info;
            this.stub = stub;
        }
    }

    public static void main(String[] args) {
        System.out.println("Initializing Main Command Terminal...");

        ManagedChannel channelAlpha = ManagedChannelBuilder.forTarget("localhost:50051").usePlaintext().build();
        ManagedChannel channelBeta = ManagedChannelBuilder.forTarget("localhost:50052").usePlaintext().build();

        DeathStarManagementGrpc.DeathStarManagementBlockingStub stubAlpha = DeathStarManagementGrpc.newBlockingStub(channelAlpha);
        DeathStarManagementGrpc.DeathStarManagementBlockingStub stubBeta = DeathStarManagementGrpc.newBlockingStub(channelBeta);

        Map<String, DeviceLocation> globalDevicesMap = new HashMap<>();
        Scanner scanner = new Scanner(System.in);

        try {
            label:
            while (true) {
                System.out.println("\nDEATH STAR MAIN SYSTEM");
                System.out.println("1. Scan Network (Fetch devices from all servers)");
                System.out.println("2. Issue Device Order (Lasers / Blast Doors)");
                System.out.println("3. Execute Scan (Life Forms / Space Scanner)");
                System.out.println("4. Exit");
                System.out.print("Selection: ");

                String choice = scanner.nextLine();

                switch (choice) {
                    case "1":
                        globalDevicesMap.clear();
                        Empty request = Empty.newBuilder().build();

                        System.out.println("\nSECTOR ALPHA DEVICES");
                        try {
                            DeviceList alphaList = stubAlpha.listDevices(request);
                            for (DeviceInfo d : alphaList.getDevicesList()) {
                                globalDevicesMap.put(d.getId(), new DeviceLocation(d, stubAlpha));
                                printDevice(d);
                            }
                        } catch (Exception e) {
                            System.out.println("[ERROR] Communication failure with Sector Alpha.");
                        }

                        System.out.println("\nSECTOR BETA DEVICES");
                        try {
                            DeviceList betaList = stubBeta.listDevices(request);
                            for (DeviceInfo d : betaList.getDevicesList()) {
                                globalDevicesMap.put(d.getId(), new DeviceLocation(d, stubBeta));
                                printDevice(d);
                            }
                        } catch (Exception e) {
                            System.out.println("[ERROR] Communication failure with Sector Beta.");
                        }

                        System.out.println("\nNetwork scan complete. Total devices found: " + globalDevicesMap.size());
                        break;

                    case "2":
                        if (globalDevicesMap.isEmpty()) {
                            System.out.println("Scan the network first (Option 1)!");
                            continue;
                        }

                        System.out.print("Enter full Device ID (e.g., ALPHA-LASER-MAIN): ");
                        String targetId = scanner.nextLine();

                        if (!globalDevicesMap.containsKey(targetId)) {
                            System.out.println("Unknown Device ID.");
                            continue;
                        }

                        DeviceLocation location = globalDevicesMap.get(targetId);
                        DeviceType type = location.info.getType();

                        ChangeStateRequest.Builder requestBuilder = ChangeStateRequest.newBuilder().setDeviceId(targetId);

                        if (type == DeviceType.HANGAR_BLAST_DOOR || type == DeviceType.INTERNAL_BLAST_DOOR) {
                            System.out.print("Blast Door Action [0-Open, 1-Close, 2-Lock Override]: ");
                            int actionIndex = Integer.parseInt(scanner.nextLine());
                            requestBuilder.setDoorAction(DoorAction.forNumber(actionIndex));

                        } else if (type == DeviceType.WEAPON_PLANET_LASER) {
                            System.out.print("Enter Superlaser power level (0-100%): ");
                            int power = Integer.parseInt(scanner.nextLine());
                            WeaponCommand weaponCmd = WeaponCommand.newBuilder().setPlanetLaserPowerPercent(power).build();
                            requestBuilder.setWeaponCommand(weaponCmd);

                        } else if (type == DeviceType.WEAPON_DEFENSIVE_LASERS) {
                            System.out.print("Coordinate X: ");
                            float x = Float.parseFloat(scanner.nextLine());
                            System.out.print("Coordinate Y: ");
                            float y = Float.parseFloat(scanner.nextLine());
                            System.out.print("Coordinate Z: ");
                            float z = Float.parseFloat(scanner.nextLine());
                            Coordinates coords = Coordinates.newBuilder().setX(x).setY(y).setZ(z).build();
                            WeaponCommand weaponCmd = WeaponCommand.newBuilder().setFireDefensiveLasers(coords).build();
                            requestBuilder.setWeaponCommand(weaponCmd);

                        } else {
                            System.out.println("This device type is not supported in the order menu. Use the scanner option.");
                            continue;
                        }

                        System.out.println("Transmitting order...");
                        try {
                            ActionResponse response = location.stub.changeDeviceState(requestBuilder.build());
                            if (response.getSuccess()) {
                                System.out.println("[SUCCESS] " + response.getMessage());
                            } else {
                                System.out.println("[CRITICAL ERROR " + response.getErrorCode() + "] " + response.getMessage());
                            }
                        } catch (Exception e) {
                            System.out.println("[ERROR] Connection lost: " + e.getMessage());
                        }
                        break;

                    case "3":
                        if (globalDevicesMap.isEmpty()) {
                            System.out.println("Scan the network first (Option 1)!");
                            continue;
                        }

                        System.out.print("Enter Scanner ID (e.g., ALPHA-SCAN-LIFE): ");
                        String scannerId = scanner.nextLine();

                        if (!globalDevicesMap.containsKey(scannerId)) {
                            System.out.println("Unknown Device ID.");
                            continue;
                        }

                        DeviceLocation scannerLocation = globalDevicesMap.get(scannerId);
                        DeviceType scannerType = scannerLocation.info.getType();

                        if (scannerType != DeviceType.LIFE_FORM_SCANNER && scannerType != DeviceType.DEVICE_SCANNER) {
                            System.out.println("The selected device is not a scanner!");
                            continue;
                        }

                        System.out.print("Target Sector to scan (e.g., Sector 4G): ");
                        String targetSector = scanner.nextLine();

                        System.out.println("Gathering sensor data...");
                        ScanRequest scanRequest = ScanRequest.newBuilder()
                                .setScannerId(scannerId)
                                .setTargetSector(targetSector)
                                .build();

                        try {
                            ScanResponse scanResponse = scannerLocation.stub.runScanner(scanRequest);
                            System.out.println("\nSCAN RESULTS");

                            if (scanResponse.getDetectedObjectsCount() == 0) {
                                System.out.println("No objects detected. Sector clear.");
                            } else {
                                for (ScanResult result : scanResponse.getDetectedObjectsList()) {
                                    // Sprawdzamy, jaka struktura przyszła w odpowiedzi (dzięki użyciu oneof)
                                    if (result.hasLifeForm()) {
                                        LifeFormDetails lf = result.getLifeForm();
                                        System.out.printf("LIFE DETECTED: Species: %s | Count: %d | Hostile: %b\n",
                                                lf.getSpecies(), lf.getCount(), lf.getIsHostile());
                                    } else if (result.hasShipOrDevice()) {
                                        ScannedDeviceDetails sd = result.getShipOrDevice();
                                        System.out.printf("OBJECT DETECTED: Class: %s | Shields Active: %b\n",
                                                sd.getObjectClass(), sd.getShieldsActive());
                                    }
                                }
                            }
                        } catch (Exception e) {
                            System.out.println("[ERROR] Sensor failure: " + e.getMessage());
                        }
                        break;

                    case "4":
                        break label;

                    default:
                        System.out.println("Invalid selection. Choose 1, 2, 3, or 4.");
                }
            }
        } finally {
            channelAlpha.shutdown();
            channelBeta.shutdown();
        }
    }

    private static void printDevice(DeviceInfo d) {
        System.out.printf("[%s] %s (Type: %s, Status: %s)\n", d.getId(), d.getName(), d.getType().name(), d.getStatus().name());
    }
}