class ServerState:

    def __init__(self):
        self.stats = {
            "total_solved": 0,
            "total_validations": 0,
            "nodes": {}
        }
        self.network = {}
        self.solving = False
        self.solution_found = False

    def update_stats(self, node_address, solved=False, validated=False):
        if node_address not in self.stats["nodes"]:
            self.stats["nodes"][node_address] = {"solved": 0, "validations": 0}
        if solved:
            self.stats["total_solved"] += 1
            self.stats["nodes"][node_address]["solved"] += 1
        if validated:
            self.stats["total_validations"] += 1
            self.stats["nodes"][node_address]["validations"] += 1

    def get_stats(self):
        node_stats = []
        for node_address, stats in self.stats["nodes"].items():
            node_stats.append({
                "address": node_address,
                "validations": stats["validations"]
            })

        return {
            "all": {
                "solved": self.stats["total_solved"],
                "validations": self.stats["total_validations"]
            },
            "nodes": node_stats
        }

    

