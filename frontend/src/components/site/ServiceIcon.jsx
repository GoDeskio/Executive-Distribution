import {
  Ship, Anchor, Flame, Coffee, Gem, Warehouse, Package, Globe, Truck,
  Container, Boxes, ShieldCheck, Plane, Building2, Factory,
} from "lucide-react";

const MAP = {
  ship: Ship, anchor: Anchor, flame: Flame, coffee: Coffee, gem: Gem,
  warehouse: Warehouse, package: Package, globe: Globe, truck: Truck,
  container: Container, boxes: Boxes, shield: ShieldCheck, plane: Plane,
  building: Building2, factory: Factory,
};

export const ICON_OPTIONS = Object.keys(MAP);

export function ServiceIcon({ name, ...props }) {
  const Icon = MAP[name] || Package;
  return <Icon {...props} />;
}
