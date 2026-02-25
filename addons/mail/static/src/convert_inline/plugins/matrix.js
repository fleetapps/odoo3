export class Band {
    top = 0;
    bottom = 0;
    clusterInfos = [];

    addClusterInfo(clusterInfo) {
        this.clusterInfos.push(clusterInfo);
        this.top = Math.min(this.top, clusterInfo.rect.top);
        this.bottom = Math.max(this.bottom, clusterInfo.rect.bottom);
    }
}
