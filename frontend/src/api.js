/**
 * API client for Digital Product Memory microservices.
 * Uses proxy paths in development, direct URLs in production.
 */

const RESOLVER_BASE = '/api/resolver';
const RECOMMENDATION_BASE = '/api/recommendation';
const REGISTRY_BASE = '/api/registry';
const PRODUCTS_BASE = '/api/products';

async function fetchJSON(url, options = {}) {
    const resp = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text}`);
    }
    return resp.json();
}

// ─── Resolver ──────────────────────────────────────────────────────────────────

export async function resolveProduct(productId, role, event) {
    const params = new URLSearchParams();
    if (role) params.set('role', role);
    if (event) params.set('event', event);
    return fetchJSON(`${RESOLVER_BASE}/resolve/${encodeURIComponent(productId)}?${params}`);
}

export async function resolveProductRaw(productId) {
    return fetchJSON(`${RESOLVER_BASE}/resolve/${encodeURIComponent(productId)}/raw`);
}

// ─── Pseudonymous client identifier ───────────────────────────────────────────
// A random identifier per browser groups the DPP templates of one client. It carries no
// personal data, and the Recommendation Engine stores only a salted hash of it.

const CLIENT_ID_KEY = 'circthread.templateClientId';
let memoryClientId = null;

function randomId() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`;
}

export function getClientId() {
    try {
        const stored = window.localStorage.getItem(CLIENT_ID_KEY);
        if (stored) return stored;
        const created = randomId();
        window.localStorage.setItem(CLIENT_ID_KEY, created);
        return created;
    } catch {
        if (!memoryClientId) memoryClientId = randomId();
        return memoryClientId;
    }
}

export async function buildCustomDpp(payload) {
    return fetchJSON(`${RESOLVER_BASE}/custom-dpp`, {
        method: 'POST',
        body: JSON.stringify({ user_id: getClientId(), ...payload }),
    });
}

// ─── Recommendation Engine ─────────────────────────────────────────────────────

export async function getRoles() {
    return fetchJSON(`${RECOMMENDATION_BASE}/ontology/roles`);
}

export async function getEvents() {
    return fetchJSON(`${RECOMMENDATION_BASE}/ontology/events`);
}

export async function getLifecyclePhases() {
    return fetchJSON(`${RECOMMENDATION_BASE}/ontology/lifecycle-phases`);
}

export async function getProductTypes() {
    return fetchJSON(`${RECOMMENDATION_BASE}/ontology/product-types`);
}

export async function getVocabularyTerms() {
    return fetchJSON(`${RECOMMENDATION_BASE}/ontology/terms`);
}

export async function getOntologyMappings() {
    return fetchJSON(`${RECOMMENDATION_BASE}/ontology/mappings`);
}

export async function getDppTemplates() {
    return fetchJSON(`${RECOMMENDATION_BASE}/templates`);
}

export async function updateDppTemplate(templateId, payload) {
    return fetchJSON(`${RECOMMENDATION_BASE}/templates/${templateId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
    });
}

export async function deleteDppTemplate(templateId) {
    return fetchJSON(`${RECOMMENDATION_BASE}/templates/${templateId}`, {
        method: 'DELETE',
    });
}

export async function getPromotedTemplateTerms() {
    return fetchJSON(`${RECOMMENDATION_BASE}/templates/promoted-terms`);
}

export async function getGraphStats() {
    return fetchJSON(`${RECOMMENDATION_BASE}/ontology/stats`);
}

// ─── Service Registry ──────────────────────────────────────────────────────────

export async function getRegisteredServices() {
    return fetchJSON(`${REGISTRY_BASE}/services`);
}

export async function registerService(serviceData) {
    return fetchJSON(`${REGISTRY_BASE}/services`, {
        method: 'POST',
        body: JSON.stringify(serviceData),
    });
}

export async function discoverService(baseUrl, register = true) {
    return fetchJSON(`${REGISTRY_BASE}/services/discover`, {
        method: 'POST',
        body: JSON.stringify({ base_url: baseUrl, register }),
    });
}

export async function deleteService(serviceId) {
    return fetchJSON(`${REGISTRY_BASE}/services/${serviceId}`, {
        method: 'DELETE',
    });
}

// ─── Mock Provider ─────────────────────────────────────────────────────────────

export async function listProducts() {
    return fetchJSON(`${RESOLVER_BASE}/products`);
}

export async function getProduct(productId) {
    return fetchJSON(`${PRODUCTS_BASE}/${productId}`);
}

// ─── Health Checks ─────────────────────────────────────────────────────────────

export async function checkHealth() {
    const services = ['resolver', 'recommendation', 'registry'];
    const bases = [RESOLVER_BASE, RECOMMENDATION_BASE, REGISTRY_BASE];
    const results = {};

    await Promise.allSettled(
        services.map(async (name, i) => {
            try {
                const resp = await fetch(`${bases[i]}/health`, { signal: AbortSignal.timeout(3000) });
                results[name] = resp.ok ? 'healthy' : 'unhealthy';
            } catch {
                results[name] = 'unreachable';
            }
        })
    );

    return results;
}
