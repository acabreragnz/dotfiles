# Changelog - Bootstrap YADM

## [2.0.0] - 2026-02-04

### 🔴 Mejoras Críticas (1-4)
- ✅ Manejo de errores con `set -e` y `set -o pipefail`
- ✅ NVM actualizado a master branch (siempre última versión)
- ✅ Cursor URL dinámica (API oficial)
- ✅ check_and_install_app con validación de errores completa

### 🟡 Mejoras Importantes (5-9)
- ✅ apt update consolidado con `ensure_apt_updated()`
- ✅ Sistema de logging completo (`~/.config/yadm/bootstrap.log`)
- ✅ Plugins ZSH con git pull (no reinstalar siempre)
- ✅ chsh con verificación `/etc/shells` y manejo de errores
- ✅ Verificación de dependencias críticas (wget, curl, git, sudo)

### 🟢 Mejoras de Calidad (10-15)
- ✅ Headers organizacionales (15 secciones)
- ✅ Contadores de progreso (`step()` - 15 pasos totales)
- ✅ Modo dry-run (`DRY_RUN=true`)
- ✅ Verificación carga NVM (nvm.sh y comando nvm)
- ✅ Trap cleanup automático para archivos temporales
- ✅ Validación de arquitectura (amd64/arm64)

### ➕ Mejoras Adicionales
- ✅ Autenticación biométrica (huella dactilar)
  - Integración con script `setup-fingerprint-auth.sh`
  - Modo `--skip-enroll` para no re-registrar

### 🧪 Testing y Herramientas
- ✅ Suite de 20 tests automatizados
- ✅ Sistema de rollback (`rollback.sh`)
- ✅ Modo dry-run funcional
- ✅ Logging estructurado con timestamps

### 📊 Estadísticas
- **Líneas de código**: 292 → 484 (+65%)
- **Funciones agregadas**: 8 nuevas funciones
- **Funciones mejoradas**: 3 funciones existentes
- **Secciones organizadas**: 15 secciones con headers
- **Tests implementados**: 20 tests automatizados

### 🔗 URLs Actualizadas
- **NVM**: `https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh`
- **Cursor**: `https://www.cursor.com/api/download?platform=linux-x64&releaseTrack=stable`

### 🎯 Funcionalidad Nueva

#### Logging
```bash
# Ver logs en tiempo real
tail -f ~/.config/yadm/bootstrap.log

# Revisar logs anteriores
cat ~/.config/yadm/bootstrap.log
```

#### Dry-Run
```bash
# Simular ejecución sin hacer cambios
DRY_RUN=true bash ~/.config/yadm/bootstrap
```

#### Testing
```bash
# Ejecutar suite completa de tests
bash ~/.config/yadm/tests/test-bootstrap.sh

# Testar bootstrap específico
bash ~/.config/yadm/tests/test-bootstrap.sh /path/to/bootstrap
```

#### Rollback
```bash
# Restaurar versión anterior
bash ~/.config/yadm/rollback.sh
```

### ⚠️ Breaking Changes
Ninguno. El bootstrap mejorado mantiene compatibilidad completa con la versión anterior.

### 🐛 Bugs Corregidos
- Plugins ZSH se reinstalaban en cada ejecución (ahora usan git pull)
- chsh podía fallar sin mensaje de error
- NVM podía instalarse sin verificar si funcionaba
- Descargas de .deb no validaban tamaño del archivo
- No había cleanup de archivos temporales en caso de error

## [1.0.0] - Original
- Bootstrap funcional básico sin mejoras
- Versiones hardcodeadas (NVM v0.39.1, Cursor 2.4)
- Sin logging estructurado
- Sin manejo de errores robusto
- Sin testing automatizado
