import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const ROOM_COLORS = [
  0x3b82f6, 0x22c55e, 0xf59e0b, 0xa855f7, 0xec4899, 0x14b8a6, 0xf97316,
];

export class FloorplanViewer {
  constructor(container) {
    this.container = container;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x17211f);

    const w = container.clientWidth || 800;
    const h = container.clientHeight || 500;
    this.camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 500);
    this.camera.position.set(20, 25, 20);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;

    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(10, 20, 10);
    this.scene.add(ambient, dir);

    this.group = new THREE.Group();
    this.scene.add(this.group);

    this._animate = this._animate.bind(this);
    requestAnimationFrame(this._animate);

    this._resizeObserver = new ResizeObserver(() => this._resize());
    this._resizeObserver.observe(container);
  }

  _resize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  _animate() {
    requestAnimationFrame(this._animate);
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  clear() {
    while (this.group.children.length) {
      const obj = this.group.children[0];
      this.group.remove(obj);
      obj.traverse?.((child) => {
        child.geometry?.dispose();
        child.material?.dispose();
      });
    }
  }

  loadScene(data) {
    this.clear();
    const wallHeight = data.wall_height ?? 8;
    const unitScale = data.unit === "m" ? 3.28084 : 1;

    data.rooms?.forEach((room, i) => {
      if (!room.polygon?.length) return;
      const shape = new THREE.Shape();
      room.polygon.forEach((p, j) => {
        const x = p.x * unitScale;
        const y = p.y * unitScale;
        if (j === 0) shape.moveTo(x, y);
        else shape.lineTo(x, y);
      });
      shape.closePath();

      const geo = new THREE.ExtrudeGeometry(shape, {
        depth: 0.08,
        bevelEnabled: false,
      });
      geo.rotateX(-Math.PI / 2);
      const mat = new THREE.MeshStandardMaterial({
        color: ROOM_COLORS[i % ROOM_COLORS.length],
        transparent: true,
        opacity: 0.55,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geo, mat);
      this.group.add(mesh);

      const label = this._makeLabel(room.name, room.polygon, unitScale);
      if (label) this.group.add(label);
    });

    data.walls?.forEach((wall) => {
      const start = wall.start;
      const end = wall.end;
      const sx = start.x * unitScale;
      const sz = start.y * unitScale;
      const ex = end.x * unitScale;
      const ez = end.y * unitScale;
      const len = Math.hypot(ex - sx, ez - sz);
      if (len < 0.01) return;

      const geo = new THREE.BoxGeometry(len, wallHeight * unitScale, (wall.thickness_ft ?? 0.33) * unitScale);
      const mat = new THREE.MeshStandardMaterial({ color: 0xd1d5db });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set((sx + ex) / 2, (wallHeight * unitScale) / 2, (sz + ez) / 2);
      mesh.rotation.y = -Math.atan2(ez - sz, ex - sx);
      this.group.add(mesh);
    });

    const grid = new THREE.GridHelper(60, 60, 0x2d3a4f, 0x1a2332);
    this.group.add(grid);

    this._frameBounds();
  }

  _makeLabel(name, polygon, scale) {
    let cx = 0;
    let cz = 0;
    polygon.forEach((p) => {
      cx += p.x;
      cz += p.y;
    });
    cx = (cx / polygon.length) * scale;
    cz = (cz / polygon.length) * scale;

    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 28px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(name, 128, 40);

    const tex = new THREE.CanvasTexture(canvas);
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
    const sprite = new THREE.Sprite(mat);
    sprite.position.set(cx, 0.5, cz);
    sprite.scale.set(4, 1, 1);
    return sprite;
  }

  _frameBounds() {
    const box = new THREE.Box3().setFromObject(this.group);
    if (box.isEmpty()) return;
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z, 1);
    this.camera.position.set(center.x + maxDim, maxDim * 1.2, center.z + maxDim);
    this.controls.target.copy(center);
    this.controls.update();
  }
}
