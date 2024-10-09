/**
 * Implements sequential client side introspection of an identifier.
 */

async function getMetadata(target) {
    try {
        const response = await fetch(target, {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        });
        return await response.json();
    } catch (error) {
        console.error(error);
    }
    return null;
}

function getTargetFromMetadata(metadata) {
    try {
        return metadata.target;
    } catch (error) {
        console.error(error);
    }
    return null;
}

export { getMetadata, getTargetFromMetadata };
