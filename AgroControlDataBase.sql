-- -----------------------------------------------------
-- Database: AgroControl
-- -----------------------------------------------------
-- DROP DATABASE IF EXISTS "AgroControl";
-- CREATE DATABASE "AgroControl";

-- CONECTARSE A LA BASE DE DATOS CREADA ANTES DE EJECUTAR EL SIGUIENTE CÓDIGO

-- -----------------------------------------------------
-- Table: roles
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    descripcion TEXT NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NULL
);

-- -----------------------------------------------------
-- Table: usuarios
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nombre_usuario VARCHAR(255) NOT NULL UNIQUE,
    correo_electronico VARCHAR(255) NULL,
    contraseña VARCHAR(255) NOT NULL,
    nombres VARCHAR(255) NULL,
    apellidos VARCHAR(255) NULL,
    rol_id INTEGER NULL,
    esta_activo BOOLEAN NULL,
    es_administrador BOOLEAN NULL,
    ultimo_acceso TIMESTAMP WITHOUT TIME ZONE NULL,
    fecha_registro TIMESTAMP WITHOUT TIME ZONE NULL,
    CONSTRAINT usuarios_rol_id_fkey FOREIGN KEY (rol_id)
        REFERENCES roles (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);

-- -----------------------------------------------------
-- Table: operarios
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS operarios (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NULL UNIQUE,
    nombre_completo VARCHAR(255) NOT NULL,
    cargo VARCHAR(255) NOT NULL,
    rut VARCHAR(255) NOT NULL UNIQUE,
    certificacion_documento VARCHAR(255) NULL,
    fecha_emision_certificacion DATE NULL,
    fecha_vencimiento_certificacion DATE NULL,
    telefono VARCHAR(255) NULL,
    esta_activo BOOLEAN NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NULL,
    actualizado_en TIMESTAMP WITHOUT TIME ZONE NULL,
    CONSTRAINT operarios_usuario_id_fkey FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);

-- -----------------------------------------------------
-- Table: equipos_agricolas
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS equipos_agricolas (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo VARCHAR(255) NOT NULL,
    modelo VARCHAR(255) NULL,
    numero_serie VARCHAR(255) NULL UNIQUE,
    fecha_compra DATE NULL,
    estado VARCHAR(255) NOT NULL,
    observaciones TEXT NULL,
    stock_actual INTEGER NOT NULL,
    stock_minimo INTEGER NOT NULL,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL
);

-- -----------------------------------------------------
-- Table: productos
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS productos (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo VARCHAR(255) NOT NULL,
    nivel_peligrosidad VARCHAR(255) NOT NULL,
    stock_actual NUMERIC NOT NULL,
    stock_minimo NUMERIC NOT NULL,
    unidad_medida VARCHAR(255) NOT NULL,
    proveedor VARCHAR(255) NULL,
    numero_registro VARCHAR(255) NULL,
    ingrediente_activo VARCHAR(255) NULL,
    concentracion VARCHAR(255) NULL,
    instrucciones_uso TEXT NULL,
    precauciones TEXT NULL,
    esta_activo BOOLEAN NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL,
    fecha_actualizacion TIMESTAMP WITH TIME ZONE NOT NULL,
    creado_por_id BIGINT NOT NULL,
    CONSTRAINT productos_creado_por_id_092f8190_fk_usuarios_id FOREIGN KEY (creado_por_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT
);

-- -----------------------------------------------------
-- Table: cuarteles_cuartel
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS cuarteles_cuartel (
    id BIGSERIAL PRIMARY KEY,
    numero VARCHAR(255) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    ubicacion TEXT NOT NULL,
    variedad VARCHAR(255) NOT NULL,
    tipo_planta VARCHAR(255) NOT NULL,
    año_plantacion INTEGER NOT NULL,
    tipo_riego VARCHAR(255) NOT NULL,
    estado_cultivo VARCHAR(255) NOT NULL,
    area_hectareas NUMERIC NOT NULL,
    observaciones TEXT NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL,
    fecha_actualizacion TIMESTAMP WITH TIME ZONE NOT NULL,
    creado_por_id INTEGER NULL,
    cantidad_hileras INTEGER NOT NULL,
    CONSTRAINT cuarteles_cuartel_creado_por_id_64136705_fk_usuarios_id FOREIGN KEY (creado_por_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);

-- -----------------------------------------------------
-- Table: cuarteles_hilera
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS cuarteles_hilera (
    id SERIAL PRIMARY KEY,
    cuartel_id BIGINT NOT NULL,
    numero_hilera INTEGER NOT NULL,
    plantas_totales_iniciales INTEGER NOT NULL,
    plantas_vivas_actuales INTEGER NOT NULL,
    plantas_muertas_actuales INTEGER NOT NULL,
    CONSTRAINT cuarteles_hilera_cuartel_id_fkey FOREIGN KEY (cuartel_id)
        REFERENCES cuarteles_cuartel (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT cuarteles_hilera_cuartel_id_numero_hilera_key UNIQUE (cuartel_id, numero_hilera)
);

-- -----------------------------------------------------
-- Table: cuarteles_seguimientocuartel
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS cuarteles_seguimientocuartel (
    id BIGSERIAL PRIMARY KEY,
    fecha_seguimiento DATE NOT NULL,
    observaciones TEXT NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL,
    cuartel_id BIGINT NOT NULL,
    responsable_id INTEGER NULL,
    CONSTRAINT cuarteles_seguimient_cuartel_id_a2d00da4_fk_cuarteles FOREIGN KEY (cuartel_id)
        REFERENCES cuarteles_cuartel (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT cuarteles_seguimient_responsable_id_9985d8aa_fk_usuarios_ FOREIGN KEY (responsable_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);

-- -----------------------------------------------------
-- Table: cuarteles_registrohilera
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS cuarteles_registrohilera (
    id SERIAL PRIMARY KEY,
    seguimiento_batch_id BIGINT NOT NULL,
    hilera_id BIGINT NOT NULL,
    observaciones_hilera TEXT NOT NULL,
    plantas_muertas_registradas INTEGER NOT NULL,
    plantas_vivas_registradas INTEGER NOT NULL,
    CONSTRAINT cuarteles_registrohilera_seguimiento_batch_id_fkey FOREIGN KEY (seguimiento_batch_id)
        REFERENCES cuarteles_seguimientocuartel (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT cuarteles_registrohilera_hilera_id_fkey FOREIGN KEY (hilera_id)
        REFERENCES cuarteles_hilera (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT
);

-- -----------------------------------------------------
-- Table: aplicaciones_fitosanitarias
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS aplicaciones_fitosanitarias (
    id BIGSERIAL PRIMARY KEY,
    fecha_aplicacion TIMESTAMP WITH TIME ZONE NOT NULL,
    area_tratada NUMERIC NULL,
    objetivo VARCHAR(255) NULL,
    metodo_aplicacion VARCHAR(255) NULL,
    estado VARCHAR(255) NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL,
    fecha_actualizacion TIMESTAMP WITH TIME ZONE NOT NULL,
    aplicador_id BIGINT NOT NULL,
    creado_por_id BIGINT NOT NULL,
    equipo_utilizado_id BIGINT NULL,
    CONSTRAINT aplicaciones_fitosan_aplicador_id_db904e3e_fk_usuarios_ FOREIGN KEY (aplicador_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT aplicaciones_fitosan_creado_por_id_66fa2830_fk_usuarios_ FOREIGN KEY (creado_por_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT aplicaciones_fitosan_equipo_utilizado_id_aca1566c_fk_equipos_a FOREIGN KEY (equipo_utilizado_id)
        REFERENCES equipos_agricolas (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);

-- -----------------------------------------------------
-- Table: aplicaciones_fitosanitarias_cuarteles
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS aplicaciones_fitosanitarias_cuarteles (
    id BIGSERIAL PRIMARY KEY,
    aplicacionfitosanitaria_id BIGINT NOT NULL,
    cuartel_id BIGINT NOT NULL,
    CONSTRAINT aplicaciones_fitosan_aplicacionfitosanita_748a2ce7_fk_aplicacio FOREIGN KEY (aplicacionfitosanitaria_id)
        REFERENCES aplicaciones_fitosanitarias (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT aplicaciones_fitosan_cuartel_id_6a00a251_fk_cuarteles FOREIGN KEY (cuartel_id)
        REFERENCES cuarteles_cuartel (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT aplicaciones_fitosanitar_aplicacionfitosanitaria__26b5f841_uniq UNIQUE (aplicacionfitosanitaria_id, cuartel_id)
);

-- -----------------------------------------------------
-- Table: aplicaciones_productos
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS aplicaciones_productos (
    id BIGSERIAL PRIMARY KEY,
    cantidad_utilizada NUMERIC NOT NULL,
    dosis_por_hectarea NUMERIC NULL,
    aplicacion_id BIGINT NOT NULL,
    producto_id BIGINT NOT NULL,
    CONSTRAINT aplicaciones_product_aplicacion_id_e1a8c3f3_fk_aplicacio FOREIGN KEY (aplicacion_id)
        REFERENCES aplicaciones_fitosanitarias (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT aplicaciones_productos_producto_id_09b26c69_fk_productos_id FOREIGN KEY (producto_id)
        REFERENCES productos (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT aplicaciones_productos_aplicacion_id_producto_id_9a6430ac_uniq UNIQUE (aplicacion_id, producto_id)
);

-- -----------------------------------------------------
-- Table: movimientos_inventario
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id BIGSERIAL PRIMARY KEY,
    tipo_movimiento VARCHAR(255) NOT NULL,
    fecha_movimiento TIMESTAMP WITH TIME ZONE NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    referencia VARCHAR(255) NULL,
    fecha_registro TIMESTAMP WITH TIME ZONE NOT NULL,
    aplicacion_id BIGINT NULL,
    realizado_por_id BIGINT NOT NULL,
    CONSTRAINT movimientos_inventar_aplicacion_id_918875e9_fk_aplicacio FOREIGN KEY (aplicacion_id)
        REFERENCES aplicaciones_fitosanitarias (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT movimientos_inventario_realizado_por_id_80242df1_fk_usuarios_id FOREIGN KEY (realizado_por_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT
);

-- -----------------------------------------------------
-- Table: detalles_movimiento
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS detalles_movimiento (
    id BIGSERIAL PRIMARY KEY,
    cantidad NUMERIC NOT NULL,
    stock_anterior NUMERIC NOT NULL,
    stock_posterior NUMERIC NOT NULL,
    movimiento_id BIGINT NOT NULL,
    producto_id BIGINT NOT NULL,
    CONSTRAINT detalles_movimiento_movimiento_id_4c6098d8_fk_movimient FOREIGN KEY (movimiento_id)
        REFERENCES movimientos_inventario (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT detalles_movimiento_producto_id_b34cef66_fk_productos_id FOREIGN KEY (producto_id)
        REFERENCES productos (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT detalles_movimiento_movimiento_id_producto_id_3ef42f70_uniq UNIQUE (movimiento_id, producto_id)
);

-- -----------------------------------------------------
-- Table: control_riego
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS control_riego (
    id BIGSERIAL PRIMARY KEY,
    horario_inicio TIME WITHOUT TIME ZONE NOT NULL,
    horario_fin TIME WITHOUT TIME ZONE NOT NULL,
    estado VARCHAR(255) NOT NULL,
    caudal_m3h NUMERIC NOT NULL,
    volumen_total_m3 NUMERIC NULL,
    incluye_fertilizante BOOLEAN NOT NULL,
    fecha DATE NOT NULL,
    duracion_minutos INTEGER NULL,
    observaciones TEXT NULL,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL,
    creado_por_id BIGINT NULL,
    cuartel_id BIGINT NOT NULL,
    encargado_riego_id BIGINT NULL,
    CONSTRAINT control_riego_creado_por_id_aba764b9_fk_usuarios_id FOREIGN KEY (creado_por_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT control_riego_cuartel_id_863e1fe2_fk_cuarteles_cuartel_id FOREIGN KEY (cuartel_id)
        REFERENCES cuarteles_cuartel (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT control_riego_encargado_riego_id_cdc4fc90_fk_usuarios_id FOREIGN KEY (encargado_riego_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);

-- -----------------------------------------------------
-- Table: control_riego_fertilizantes
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS control_riego_fertilizantes (
    id BIGSERIAL PRIMARY KEY,
    cantidad_kg NUMERIC NOT NULL,
    control_riego_id BIGINT NOT NULL,
    producto_id BIGINT NOT NULL,
    CONSTRAINT control_riego_fertil_control_riego_id_a18fa923_fk_control_r FOREIGN KEY (control_riego_id)
        REFERENCES control_riego (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT control_riego_fertilizan_control_riego_id_product_58d3e26f_uniq UNIQUE (control_riego_id, producto_id),
    CONSTRAINT control_riego_fertilizantes_producto_id_fkey FOREIGN KEY (producto_id)
        REFERENCES productos (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT
);

-- -----------------------------------------------------
-- Table: mantenimiento_mantenimiento
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS mantenimiento_mantenimiento (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(255) NOT NULL,
    estado VARCHAR(255) NOT NULL,
    fecha_programada DATE NOT NULL,
    fecha_realizacion DATE NULL,
    descripcion TEXT NOT NULL,
    costo_estimado NUMERIC NOT NULL,
    costo_real NUMERIC NOT NULL,
    observaciones TEXT NULL,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL,
    creado_por_id BIGINT NULL,
    maquinaria_id BIGINT NOT NULL, -- Asumo que maquinaria_id hace referencia a equipos_agricolas.id aunque no se especificó FK.
    operario_id BIGINT NULL,
    responsable_id BIGINT NOT NULL,
    CONSTRAINT mantenimiento_manten_creado_por_id_c30362f1_fk_usuarios_ FOREIGN KEY (creado_por_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT mantenimiento_mantenimiento_operario_id_372683fa_fk_usuarios_id FOREIGN KEY (operario_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT mantenimiento_manten_responsable_id_02c52dd1_fk_usuarios_ FOREIGN KEY (responsable_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT mantenimiento_mantenimiento_maquinaria_id_fkey FOREIGN KEY (maquinaria_id)
        REFERENCES equipos_agricolas (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT
);

-- -----------------------------------------------------
-- Table: mantenimientos
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS mantenimientos (
    id BIGSERIAL PRIMARY KEY,
    fecha_mantenimiento TIMESTAMP WITH TIME ZONE NOT NULL,
    descripcion_trabajo TEXT NOT NULL,
    tipo_mantenimiento VARCHAR(255) NOT NULL,
    estado VARCHAR(255) NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL,
    fecha_actualizacion TIMESTAMP WITH TIME ZONE NOT NULL,
    creado_por_id BIGINT NULL,
    maquinaria_id BIGINT NOT NULL,
    operario_responsable_id BIGINT NULL,
    cantidad INTEGER NOT NULL,
    CONSTRAINT mantenimientos_creado_por_id_8041ed8a_fk_usuarios_id FOREIGN KEY (creado_por_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT mantenimientos_maquinaria_id_c8b7a5e1_fk_equipos_agricolas_id FOREIGN KEY (maquinaria_id)
        REFERENCES equipos_agricolas (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT mantenimientos_operario_responsable_id_a15f2a3d_fk_usuarios_id FOREIGN KEY (operario_responsable_id)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);


-- -----------------------------------------------------
-- Table: fertilizaciones
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS fertilizaciones (
    id SERIAL PRIMARY KEY,
    cuartel_id INTEGER NULL, -- Sin FK especificada, pero podría apuntar a cuarteles_cuartel.id
    fecha DATE NOT NULL,
    producto VARCHAR(255) NOT NULL, -- Podría apuntar a productos.id, pero es VARCHAR
    cantidad_aplicada NUMERIC NOT NULL,
    unidad VARCHAR(255) NOT NULL,
    sector VARCHAR(255) NULL,
    operario_id INTEGER NULL,
    observaciones TEXT NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NULL,
    creado_por INTEGER NULL,
    CONSTRAINT fertilizaciones_operario_id_fkey FOREIGN KEY (operario_id)
        REFERENCES operarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT fertilizaciones_creado_por_fkey FOREIGN KEY (creado_por)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);

-- -----------------------------------------------------
-- Table: tareas_operarios
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS tareas_operarios (
    id SERIAL PRIMARY KEY,
    operario_id INTEGER NULL,
    tipo_tarea VARCHAR(255) NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_asignacion DATE NOT NULL,
    fecha_vencimiento DATE NULL,
    fecha_completada DATE NULL,
    estado VARCHAR(255) NULL,
    cuartel_id INTEGER NULL, -- Sin FK especificada, podría apuntar a cuarteles_cuartel.id
    prioridad VARCHAR(255) NULL,
    observaciones TEXT NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NULL,
    creado_por INTEGER NULL,
    CONSTRAINT tareas_operarios_operario_id_fkey FOREIGN KEY (operario_id)
        REFERENCES operarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT tareas_operarios_creado_por_fkey FOREIGN KEY (creado_por)
        REFERENCES usuarios (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
);